from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, session, jsonify
from flask_login import login_user, logout_user, current_user, login_required
from urllib.parse import urlparse
from app import db
from app.models import User, Game, Checklist, ChecklistItem, UserChecklist, UserProgress, Reward, ItemReward, ItemPrerequisite
from app.forms import RegistrationForm, LoginForm, ChecklistForm, ChecklistItemForm, GameForm, ChecklistEditForm
from app.ai_service import generate_checklist_items
from datetime import datetime
from sqlalchemy import func
import logging
import functools

logger = logging.getLogger(__name__)

def log_function_call(func):
    """Decorator to log function calls with parameters."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # For route handlers, log the endpoint and request info
        logger.debug(f"{func.__name__} called with args={args}, kwargs={kwargs}")
        return func(*args, **kwargs)
    return wrapper

main_bp = Blueprint('main', __name__)
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')
checklist_bp = Blueprint('checklist', __name__, url_prefix='/checklist')

@log_function_call
def is_safe_redirect_url(target):
    """
    Validates that a redirect URL is safe (relative to the current domain).
    Returns True only if the URL has no netloc (network location/domain),
    preventing open redirect vulnerabilities.
    """
    if not target:
        return False
    parsed = urlparse(target)
    return parsed.netloc == '' and parsed.scheme == ''

@log_function_call
def get_selected_game():
    """Get the currently selected game from session."""
    return session.get('selected_game')

@log_function_call
def set_selected_game(game_name):
    """Set the currently selected game in session."""
    session['selected_game'] = game_name

@log_function_call
def clear_selected_game():
    """Clear the currently selected game from session."""
    session.pop('selected_game', None)

@main_bp.route('/')
@log_function_call
def index():
    public_checklists = Checklist.query.filter_by(is_public=True).order_by(Checklist.created_at.desc()).limit(10).all()
    return render_template('index.html', checklists=public_checklists)

@main_bp.route('/games')
@log_function_call
def games():
    """Unified games page showing all games with search capability."""
    search_query = request.args.get('search', '').strip()
    
    # Get all games
    if search_query:
        games_list = Game.query.filter(Game.name.ilike(f'%{search_query}%')).order_by(Game.name).all()
    else:
        games_list = Game.query.order_by(Game.name).all()
    
    # For authenticated users, get their stats
    game_stats = {}
    if current_user.is_authenticated:
        for game in games_list:
            # Count public checklists for this game
            public_count = Checklist.query.filter_by(is_public=True, game_id=game.id).count()
            # Count user's created checklists
            created_count = current_user.created_checklists.filter_by(game_id=game.id).count()
            # Count user's copied checklists
            copied_count = db.session.query(UserChecklist).join(
                Checklist, Checklist.id == UserChecklist.checklist_id
            ).filter(
                UserChecklist.user_id == current_user.id,
                Checklist.game_id == game.id
            ).count()
            game_stats[game.id] = {
                'public': public_count,
                'created': created_count,
                'copied': copied_count
            }
    else:
        # For non-authenticated users, just show public counts
        for game in games_list:
            public_count = Checklist.query.filter_by(is_public=True, game_id=game.id).count()
            game_stats[game.id] = {'public': public_count}
    
    return render_template('games.html', games=games_list, game_stats=game_stats, search_query=search_query)

@main_bp.route('/games/new', methods=['GET', 'POST'])
@login_required
@log_function_call
def add_game():
    """Add a new game to the system."""
    form = GameForm()
    if form.validate_on_submit():
        game = Game(name=form.name.data)
        db.session.add(game)
        db.session.commit()
        flash(f'Game "{game.name}" added successfully!', 'success')
        return redirect(url_for('main.game_detail', game_id=game.id))
    
    return render_template('add_game.html', form=form)

@main_bp.route('/games/<int:game_id>')
@log_function_call
def game_detail(game_id):
    """Game detail page showing all checklists for a game."""
    game = db.session.get(Game, game_id)
    if not game:
        abort(404)
    
    page = request.args.get('page', 1, type=int)
    
    # Get public checklists for this game
    public_checklists = Checklist.query.filter_by(
        is_public=True, 
        game_id=game_id
    ).order_by(Checklist.created_at.desc()).all()
    
    # Get user's checklists for this game if authenticated
    user_created = []
    user_copied = []
    if current_user.is_authenticated:
        user_created = current_user.created_checklists.filter_by(
            game_id=game_id
        ).order_by(Checklist.created_at.desc()).all()
        
        user_copied = db.session.query(UserChecklist).join(
            Checklist, Checklist.id == UserChecklist.checklist_id
        ).filter(
            UserChecklist.user_id == current_user.id,
            Checklist.game_id == game_id
        ).all()
    
    return render_template('game_detail.html', game=game, 
                         public_checklists=public_checklists,
                         user_created=user_created,
                         user_copied=user_copied)

@main_bp.route('/browse')
@log_function_call
def browse():
    """Legacy route - redirect to games page."""
    return redirect(url_for('main.games'))

@main_bp.route('/browse/<int:game_id>')
@log_function_call
def browse_game(game_id):
    """Legacy route - redirect to game detail page."""
    return redirect(url_for('main.game_detail', game_id=game_id))

@auth_bp.route('/register', methods=['GET', 'POST'])
@log_function_call
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('register.html', form=form)

@auth_bp.route('/login', methods=['GET', 'POST'])
@log_function_call
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            next_page = request.args.get('next')
            flash('Login successful!', 'success')
            # Prevent open redirect vulnerability by validating the redirect target
            if is_safe_redirect_url(next_page):
                return redirect(next_page)
            return redirect(url_for('main.index'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html', form=form)

@auth_bp.route('/logout')
@login_required
@log_function_call
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))

@checklist_bp.route('/create', methods=['GET', 'POST'])
@checklist_bp.route('/create/<int:game_id>', methods=['GET', 'POST'])
@login_required
@log_function_call
def create(game_id=None):
    """Create a new checklist, optionally for a specific game."""
    game = None
    if game_id:
        game = db.session.get(Game, game_id)
        if not game:
            abort(404)
    
    form = ChecklistForm()
    
    # Pre-populate game_name if a game is specified
    if request.method == 'GET' and game:
        form.game_name.data = game.name
    
    if form.validate_on_submit():
        # Get or create the game
        game = Game.query.filter_by(name=form.game_name.data).first()
        if not game:
            game = Game(name=form.game_name.data)
            db.session.add(game)
            db.session.flush()  # Get the game ID
        
        checklist = Checklist(
            title=form.title.data,
            game_id=game.id,
            description=form.description.data,
            is_public=form.is_public.data,
            creator_id=current_user.id
        )
        db.session.add(checklist)
        db.session.commit()
        
        # If AI prompt is provided, generate items
        if form.ai_prompt.data and form.ai_prompt.data.strip():
            generated_items = generate_checklist_items(
                game_name=form.game_name.data,
                title=form.title.data,
                prompt=form.ai_prompt.data,
                description=form.description.data or ""
            )
            
            if generated_items:
                # Add generated items to the checklist
                for index, item_data in enumerate(generated_items):
                    item = ChecklistItem(
                        checklist_id=checklist.id,
                        title=item_data['title'],
                        description=item_data.get('description', ''),
                        order=index + 1
                    )
                    db.session.add(item)
                db.session.commit()
                flash(f'Checklist created with {len(generated_items)} AI-generated items!', 'success')
            else:
                flash('Checklist created, but AI generation failed. Please add items manually.', 'warning')
        else:
            flash('Checklist created successfully! You can now add items.', 'success')
        
        return redirect(url_for('checklist.view', checklist_id=checklist.id))
    
    return render_template('create_checklist.html', form=form, game=game)

@checklist_bp.route('/<int:checklist_id>')
@log_function_call
def view(checklist_id):
    checklist = Checklist.query.get_or_404(checklist_id)
    
    if not checklist.is_public and (not current_user.is_authenticated or checklist.creator_id != current_user.id):
        abort(403)
    
    items = checklist.items.all()
    user_copy = None
    progress = {}
    effective_progress = {}  # Track effective completion (considers prerequisites)
    item_locked = {}  # Track which items are locked due to prerequisites
    reward_tallies = {}  # Track reward tallies for checking prerequisites
    
    if current_user.is_authenticated:
        user_copy = UserChecklist.query.filter_by(
            user_id=current_user.id,
            checklist_id=checklist_id
        ).first()
        
        if user_copy:
            # Calculate all reward tallies for prerequisite checking
            # We need to calculate for each unique combination of reward, location, and category
            for item in items:
                for prereq in item.prerequisites:
                    if prereq.prerequisite_reward_id:
                        # Create a key for this specific reward with filters
                        key = (prereq.prerequisite_reward_id, prereq.reward_location, prereq.reward_category)
                        if key not in reward_tallies:
                            reward_tallies[key] = user_copy.get_reward_tally(
                                reward_id=prereq.prerequisite_reward_id,
                                location=prereq.reward_location,
                                category=prereq.reward_category
                            )
            
            for item in items:
                prog = UserProgress.query.filter_by(
                    user_checklist_id=user_copy.id,
                    item_id=item.id
                ).first()
                # Store the actual completion state from database
                progress[item.id] = prog.completed if prog else False
                
                # Check if item is locked due to prerequisites
                prereqs_met, unmet_prereqs = item.are_prerequisites_met(user_copy.id)
                item_locked[item.id] = not prereqs_met
                
                # Effective completion: only true if actually completed AND prerequisites are met
                # This ensures locked items don't count as completed for display/rewards
                effective_progress[item.id] = progress[item.id] and prereqs_met
    
    return render_template('view_checklist.html', checklist=checklist, items=items, 
                         user_copy=user_copy, progress=progress, effective_progress=effective_progress,
                         item_locked=item_locked, reward_tallies=reward_tallies)

@checklist_bp.route('/<int:checklist_id>/edit', methods=['GET', 'POST'])
@login_required
@log_function_call
def edit(checklist_id):
    """Edit a checklist that the user created."""
    checklist = Checklist.query.get_or_404(checklist_id)
    
    # Only the creator can edit their checklist
    if checklist.creator_id != current_user.id:
        abort(403)
    
    form = ChecklistEditForm()
    
    if form.validate_on_submit():
        # Update basic checklist information
        checklist.title = form.title.data
        checklist.description = form.description.data
        checklist.is_public = form.is_public.data
        
        # If AI prompt is provided, generate additional items
        if form.ai_prompt.data and form.ai_prompt.data.strip():
            generated_items = generate_checklist_items(
                game_name=checklist.game.name,
                title=form.title.data,
                prompt=form.ai_prompt.data,
                description=form.description.data or ""
            )
            
            if generated_items:
                # Get the max order to append new items
                max_order = db.session.query(func.max(ChecklistItem.order)).filter_by(
                    checklist_id=checklist_id
                ).scalar() or 0
                
                # Add generated items to the checklist
                for index, item_data in enumerate(generated_items):
                    item = ChecklistItem(
                        checklist_id=checklist.id,
                        title=item_data['title'],
                        description=item_data.get('description', ''),
                        order=max_order + index + 1
                    )
                    db.session.add(item)
                
                flash(f'Checklist updated with {len(generated_items)} AI-generated items!', 'success')
            else:
                flash('Checklist updated, but AI generation failed.', 'warning')
        else:
            flash('Checklist updated successfully!', 'success')
        
        db.session.commit()
        
        return redirect(url_for('checklist.view', checklist_id=checklist.id))
    
    # Pre-populate form with existing data
    if request.method == 'GET':
        form.title.data = checklist.title
        form.description.data = checklist.description
        form.is_public.data = checklist.is_public
    
    # Get all items for this checklist
    items = checklist.items.order_by(ChecklistItem.order).all()
    
    return render_template('edit_checklist.html', form=form, checklist=checklist, items=items)

@checklist_bp.route('/<int:checklist_id>/batch-update', methods=['POST'])
@login_required
@log_function_call
def batch_update(checklist_id):
    """Batch update checklist metadata and items."""
    checklist = Checklist.query.get_or_404(checklist_id)
    
    # Only the creator can edit their checklist
    if checklist.creator_id != current_user.id:
        abort(403)
    
    data = request.get_json()
    
    try:
        # Update basic checklist information
        checklist.title = data.get('title', checklist.title)
        checklist.description = data.get('description', checklist.description)
        checklist.is_public = data.get('is_public', checklist.is_public)
        
        # Handle items
        items_data = data.get('items', [])
        existing_item_ids = set()
        
        # Update or create items
        for idx, item_data in enumerate(items_data):
            item_id = item_data.get('id')
            
            if item_id and item_id != 'new':
                # Update existing item
                item = ChecklistItem.query.get(item_id)
                if item and item.checklist_id == checklist_id:
                    item.title = item_data.get('title', item.title)
                    item.description = item_data.get('description', item.description)
                    item.location = item_data.get('location', item.location)
                    item.category = item_data.get('category', item.category)
                    item.order = idx + 1
                    
                    # Handle rewards
                    reward_data = item_data.get('rewards', [])
                    if reward_data is not None:
                        # Clear existing reward associations
                        ItemReward.query.filter_by(checklist_item_id=item.id).delete()
                        
                        # Add new rewards with amounts
                        for reward_info in reward_data:
                            # Handle both old format (string) and new format (object with name and amount)
                            if isinstance(reward_info, str):
                                reward_name = reward_info.strip()
                                reward_amount = 1
                            else:
                                reward_name = reward_info.get('name', '').strip()
                                reward_amount = reward_info.get('amount', 1)
                            
                            if reward_name:
                                # Get or create reward
                                reward = Reward.query.filter_by(name=reward_name).first()
                                if not reward:
                                    reward = Reward(name=reward_name)
                                    db.session.add(reward)
                                    db.session.flush()  # Get the reward ID
                                
                                # Create association with amount
                                item_reward = ItemReward(
                                    checklist_item_id=item.id,
                                    reward_id=reward.id,
                                    amount=reward_amount
                                )
                                db.session.add(item_reward)
                    
                    # Handle prerequisites
                    prereq_data = item_data.get('prerequisites', [])
                    if prereq_data is not None:
                        # Clear existing prerequisites
                        ItemPrerequisite.query.filter_by(item_id=item.id).delete()
                        
                        # Add new prerequisites
                        for prereq_info in prereq_data:
                            prereq_type = prereq_info.get('type')
                            
                            if prereq_type == 'item':
                                # Prerequisite is another checklist item
                                prereq_item_id = prereq_info.get('prerequisite_item_id')
                                if prereq_item_id:
                                    prereq = ItemPrerequisite(
                                        item_id=item.id,
                                        prerequisite_item_id=prereq_item_id
                                    )
                                    db.session.add(prereq)
                            
                            elif prereq_type == 'reward':
                                # Prerequisite is a reward
                                reward_name = prereq_info.get('reward_name', '').strip()
                                if reward_name:
                                    # Get or create reward
                                    reward = Reward.query.filter_by(name=reward_name).first()
                                    if not reward:
                                        reward = Reward(name=reward_name)
                                        db.session.add(reward)
                                        db.session.flush()
                                    
                                    consumes = prereq_info.get('consumes_reward', False)
                                    reward_amount = prereq_info.get('reward_amount', 1)
                                    reward_location = prereq_info.get('reward_location', '').strip() or None
                                    reward_category = prereq_info.get('reward_category', '').strip() or None
                                    prereq = ItemPrerequisite(
                                        item_id=item.id,
                                        prerequisite_reward_id=reward.id,
                                        reward_amount=reward_amount,
                                        consumes_reward=consumes,
                                        reward_location=reward_location,
                                        reward_category=reward_category
                                    )
                                    db.session.add(prereq)
                            
                            elif prereq_type == 'freeform':
                                # Freeform text prerequisite
                                freeform_text = prereq_info.get('freeform_text', '').strip()
                                if freeform_text:
                                    prereq = ItemPrerequisite(
                                        item_id=item.id,
                                        freeform_text=freeform_text
                                    )
                                    db.session.add(prereq)
                    
                    existing_item_ids.add(item_id)
            else:
                # Create new item
                new_item = ChecklistItem(
                    checklist_id=checklist_id,
                    title=item_data.get('title', ''),
                    description=item_data.get('description', ''),
                    location=item_data.get('location', ''),
                    category=item_data.get('category', ''),
                    order=idx + 1
                )
                db.session.add(new_item)
                db.session.flush()  # Get the new item ID
                
                # Sync progress entries for all user copies
                ChecklistItem.sync_progress_for_new_item(new_item.id, checklist_id)
                
                # Handle rewards for new item
                reward_data = item_data.get('rewards', [])
                if reward_data:
                    for reward_info in reward_data:
                        # Handle both old format (string) and new format (object with name and amount)
                        if isinstance(reward_info, str):
                            reward_name = reward_info.strip()
                            reward_amount = 1
                        else:
                            reward_name = reward_info.get('name', '').strip()
                            reward_amount = reward_info.get('amount', 1)
                        
                        if reward_name:
                            # Get or create reward
                            reward = Reward.query.filter_by(name=reward_name).first()
                            if not reward:
                                reward = Reward(name=reward_name)
                                db.session.add(reward)
                                db.session.flush()  # Get the reward ID
                            
                            # Create association with amount
                            item_reward = ItemReward(
                                checklist_item_id=new_item.id,
                                reward_id=reward.id,
                                amount=reward_amount
                            )
                            db.session.add(item_reward)
                
                # Handle prerequisites for new item
                prereq_data = item_data.get('prerequisites', [])
                if prereq_data:
                    for prereq_info in prereq_data:
                        prereq_type = prereq_info.get('type')
                        
                        if prereq_type == 'item':
                            # Prerequisite is another checklist item
                            prereq_item_id = prereq_info.get('prerequisite_item_id')
                            if prereq_item_id:
                                prereq = ItemPrerequisite(
                                    item_id=new_item.id,
                                    prerequisite_item_id=prereq_item_id
                                )
                                db.session.add(prereq)
                        
                        elif prereq_type == 'reward':
                            # Prerequisite is a reward
                            reward_name = prereq_info.get('reward_name', '').strip()
                            if reward_name:
                                # Get or create reward
                                reward = Reward.query.filter_by(name=reward_name).first()
                                if not reward:
                                    reward = Reward(name=reward_name)
                                    db.session.add(reward)
                                    db.session.flush()
                                
                                consumes = prereq_info.get('consumes_reward', False)
                                reward_amount = prereq_info.get('reward_amount', 1)
                                reward_location = prereq_info.get('reward_location', '').strip() or None
                                reward_category = prereq_info.get('reward_category', '').strip() or None
                                prereq = ItemPrerequisite(
                                    item_id=new_item.id,
                                    prerequisite_reward_id=reward.id,
                                    reward_amount=reward_amount,
                                    consumes_reward=consumes,
                                    reward_location=reward_location,
                                    reward_category=reward_category
                                )
                                db.session.add(prereq)
                        
                        elif prereq_type == 'freeform':
                            # Freeform text prerequisite
                            freeform_text = prereq_info.get('freeform_text', '').strip()
                            if freeform_text:
                                prereq = ItemPrerequisite(
                                    item_id=new_item.id,
                                    freeform_text=freeform_text
                                )
                                db.session.add(prereq)
        
        # Delete items that were removed
        deleted_ids = data.get('deleted_items', [])
        for item_id in deleted_ids:
            item = ChecklistItem.query.get(item_id)
            if item and item.checklist_id == checklist_id:
                # Explicitly delete associated UserProgress entries
                # This ensures cleanup works regardless of database FK enforcement
                UserProgress.query.filter_by(item_id=item_id).delete()
                db.session.delete(item)
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Checklist updated successfully!'})
    except Exception as e:
        db.session.rollback()
        # Log the actual error for debugging
        import logging
        logging.error(f"Error updating checklist {checklist_id}: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to update checklist. Please try again.'}), 400

@checklist_bp.route('/<int:checklist_id>/add_item', methods=['GET', 'POST'])
@login_required
@log_function_call
def add_item(checklist_id):
    checklist = Checklist.query.get_or_404(checklist_id)
    
    if checklist.creator_id != current_user.id:
        abort(403)
    
    form = ChecklistItemForm()
    if form.validate_on_submit():
        max_order = db.session.query(db.func.max(ChecklistItem.order)).filter_by(
            checklist_id=checklist_id
        ).scalar() or 0
        
        item = ChecklistItem(
            checklist_id=checklist_id,
            title=form.title.data,
            description=form.description.data,
            location=form.location.data,
            category=form.category.data,
            order=max_order + 1
        )
        db.session.add(item)
        db.session.flush()  # Get the item ID
        
        # Sync progress entries for all user copies
        ChecklistItem.sync_progress_for_new_item(item.id, checklist_id)
        
        db.session.commit()
        flash('Item added successfully!', 'success')
        return redirect(url_for('checklist.view', checklist_id=checklist_id))
    
    return render_template('add_item.html', form=form, checklist=checklist)

@checklist_bp.route('/<int:checklist_id>/copy', methods=['POST'])
@login_required
@log_function_call
def copy(checklist_id):
    checklist = Checklist.query.get_or_404(checklist_id)
    
    if not checklist.is_public and checklist.creator_id != current_user.id:
        abort(403)
    
    existing = UserChecklist.query.filter_by(
        user_id=current_user.id,
        checklist_id=checklist_id
    ).first()
    
    if existing:
        flash('You already have a copy of this checklist!', 'warning')
        return redirect(url_for('main.game_detail', game_id=checklist.game_id))
    
    user_checklist = UserChecklist(user_id=current_user.id, checklist_id=checklist_id)
    db.session.add(user_checklist)
    db.session.commit()
    
    for item in checklist.items.all():
        progress = UserProgress(
            user_checklist_id=user_checklist.id,
            item_id=item.id,
            completed=False
        )
        db.session.add(progress)
    
    db.session.commit()
    
    flash('Checklist copied to your account!', 'success')
    return redirect(url_for('main.game_detail', game_id=checklist.game_id))

@log_function_call
def are_prerequisites_met_with_chaining(item, user_checklist_id, checked_items=None):
    """
    Check if prerequisites are met, considering the chaining of locked items.
    
    An item's prerequisites are met only if:
    1. Direct prerequisites are met (items completed, rewards available)
    2. For prerequisite items: those items' prerequisites are also met (recursive)
    
    This prevents the situation where:
    - Item B requires Item A
    - Item C requires Item B
    - If A is unchecked, B becomes locked
    - C should also be locked because B is locked (even though B is still marked completed in DB)
    
    Args:
        item: ChecklistItem to check
        user_checklist_id: ID of user's checklist
        checked_items: Set of item IDs already checked (to prevent infinite loops)
        
    Returns:
        tuple: (bool, list) - (are_met, list_of_unmet_prerequisites)
    """
    if checked_items is None:
        checked_items = set()
    
    # Prevent infinite loops in circular dependencies
    if item.id in checked_items:
        return (True, [])
    
    checked_items.add(item.id)
    unmet = []
    
    for prereq in item.prerequisites:
        # Type 1: Prerequisite checklist item
        if prereq.prerequisite_item_id:
            if user_checklist_id:
                # Check if the prerequisite item is completed
                progress = UserProgress.query.filter_by(
                    user_checklist_id=user_checklist_id,
                    item_id=prereq.prerequisite_item_id
                ).first()
                
                if not progress or not progress.completed:
                    unmet.append(prereq)
                else:
                    # Item is completed, but we also need to check if ITS prerequisites are met
                    # (this is the chaining part)
                    prereq_item = ChecklistItem.query.get(prereq.prerequisite_item_id)
                    if prereq_item:
                        prereq_met, _ = are_prerequisites_met_with_chaining(
                            prereq_item, user_checklist_id, checked_items
                        )
                        if not prereq_met:
                            # The prerequisite item's prerequisites aren't met,
                            # so this item is effectively locked
                            unmet.append(prereq)
            else:
                # Can't verify completion without user_checklist_id
                unmet.append(prereq)
        
        # Type 2: Prerequisite reward - check if user has collected enough
        elif prereq.prerequisite_reward_id:
            if user_checklist_id:
                # Calculate the reward tally with filters
                # Pass checked_items to avoid infinite loops when checking
                # items that provide rewards used in their own prerequisites
                collected = get_available_rewards_with_chaining(
                    user_checklist_id,
                    prereq.prerequisite_reward_id,
                    prereq.reward_location,
                    prereq.reward_category,
                    checked_items
                )
                required = prereq.reward_amount or 1
                
                # Check if user has collected enough of this reward
                if collected < required:
                    unmet.append(prereq)
            else:
                # Can't verify completion without user_checklist_id
                unmet.append(prereq)
        
        # Type 3: Freeform text (informational only)
        elif prereq.freeform_text:
            # Freeform prerequisites are informational, don't block completion
            pass
    
    return (len(unmet) == 0, unmet)

@log_function_call
def get_available_rewards_with_chaining(user_checklist_id, reward_id, location, category, checked_items):
    """
    Calculate available rewards considering prerequisite chaining.
    
    Only count rewards from items that:
    1. Are completed
    2. Have their prerequisites met (recursively)
    
    Args:
        user_checklist_id: ID of user's checklist
        reward_id: Reward ID to count
        location: Location filter (or None)
        category: Category filter (or None)
        checked_items: Set of already checked items to prevent loops
        
    Returns:
        int: Available amount of the reward
    """
    user_checklist = db.session.get(UserChecklist, user_checklist_id)
    if not user_checklist:
        return 0
    
    # Get all completed items for this user checklist
    completed_progress = user_checklist.progress_items.filter_by(completed=True).all()
    completed_item_ids = [p.item_id for p in completed_progress]
    
    if not completed_item_ids:
        return 0
    
    # Query for items with rewards
    query = db.session.query(ChecklistItem, ItemReward).join(
        ItemReward, ChecklistItem.id == ItemReward.checklist_item_id
    ).filter(
        ChecklistItem.id.in_(completed_item_ids),
        ItemReward.reward_id == reward_id
    )
    
    # Apply location filter if specified
    if location is not None:
        query = query.filter(ChecklistItem.location == location)
    
    # Apply category filter if specified
    if category is not None:
        query = query.filter(ChecklistItem.category == category)
    
    results = query.all()
    
    # Sum up rewards, but only from items whose prerequisites are met
    total = 0
    for check_item, item_reward in results:
        # Skip items that are currently being checked (to avoid circular logic)
        if check_item.id in checked_items:
            continue
            
        # Check if this item's prerequisites are met (with chaining)
        prereqs_met, _ = are_prerequisites_met_with_chaining(
            check_item, user_checklist_id, checked_items.copy()
        )
        if prereqs_met:
            total += item_reward.amount
    
    return total

@log_function_call
def get_affected_items_recursive(checklist_id, user_checklist_id, changed_item_id, is_now_completed):
    """
    Recursively find all items affected by toggling a checklist item.
    
    This implements proper prerequisite chaining:
    - When an item is checked/unchecked, it may affect items that depend on it
    - Those affected items may in turn affect other items that depend on them
    - This continues recursively until no more items are affected
    
    Args:
        checklist_id: ID of the checklist
        user_checklist_id: ID of the user's checklist instance
        changed_item_id: ID of the item that was just toggled
        is_now_completed: Whether the item is now completed (True) or uncompleted (False)
        
    Returns:
        tuple: (unlocked_item_ids, locked_item_ids) - lists of item IDs
    """
    unlocked_items = []
    locked_items = []
    processed_items = {changed_item_id}  # Track items we've already processed to avoid loops
    items_to_check = []  # Queue of items to check for cascading effects
    
    # Start by finding immediate dependencies of the changed item
    changed_item = ChecklistItem.query.get(changed_item_id)
    if not changed_item:
        return unlocked_items, locked_items
    
    # Find all items with item prerequisites on the changed item
    dependent_prereqs = ItemPrerequisite.query.filter_by(
        prerequisite_item_id=changed_item_id
    ).all()
    
    for prereq in dependent_prereqs:
        if prereq.item_id not in processed_items:
            items_to_check.append(prereq.item_id)
    
    # Find all items with reward prerequisites that might be affected
    # We need to check ALL items when ANY item is toggled, because:
    # 1. The changed item might provide rewards that other items need
    # 2. The changed item might have become locked, affecting reward availability
    all_items = ChecklistItem.query.filter_by(checklist_id=checklist_id).all()
    
    for check_item in all_items:
        if check_item.id == changed_item_id or check_item.id in processed_items:
            continue
        
        # Check if this item has any reward prerequisites
        # (these might be affected by the change)
        has_reward_prereq = any(prereq.prerequisite_reward_id for prereq in check_item.prerequisites)
        if has_reward_prereq:
            if check_item.id not in items_to_check:
                items_to_check.append(check_item.id)
    
    # Process all potentially affected items recursively
    while items_to_check:
        item_id = items_to_check.pop(0)
        
        if item_id in processed_items:
            continue
            
        processed_items.add(item_id)
        
        item = ChecklistItem.query.get(item_id)
        if not item or item.checklist_id != checklist_id:
            continue
        
        # Check if this item's prerequisites are met (with chaining)
        are_met, unmet = are_prerequisites_met_with_chaining(item, user_checklist_id)
        
        if are_met:
            # Prerequisites are met - item should be unlocked
            if item_id not in unlocked_items:
                unlocked_items.append(item_id)
                # This item becoming unlocked might unlock other items, so add them to check
                _add_dependent_items(item_id, checklist_id, items_to_check, processed_items)
        else:
            # Prerequisites are not met - item should be locked
            if item_id not in locked_items:
                locked_items.append(item_id)
                # This item becoming locked might lock other items, so add them to check
                _add_dependent_items(item_id, checklist_id, items_to_check, processed_items)
    
    return unlocked_items, locked_items

@log_function_call
def _add_dependent_items(item_id, checklist_id, items_to_check, processed_items):
    """
    Helper to add items that depend on the given item to the check queue.
    
    Args:
        item_id: ID of the item whose dependents to find
        checklist_id: ID of the checklist
        items_to_check: List to append dependent items to
        processed_items: Set of already processed items
    """
    # Find items with item prerequisites on this item
    dependent_prereqs = ItemPrerequisite.query.filter_by(
        prerequisite_item_id=item_id
    ).all()
    
    for prereq in dependent_prereqs:
        if prereq.item_id not in processed_items and prereq.item_id not in items_to_check:
            items_to_check.append(prereq.item_id)
    
    # Find items with reward prerequisites that might depend on this item's rewards
    item = ChecklistItem.query.get(item_id)
    if item:
        item_reward_ids = [ir.reward_id for ir in item.rewards]
        if item_reward_ids:
            all_items = ChecklistItem.query.filter_by(checklist_id=checklist_id).all()
            
            for check_item in all_items:
                if check_item.id in processed_items or check_item.id in items_to_check:
                    continue
                    
                # Check if this item has reward prerequisites for any rewards from the item
                for prereq in check_item.prerequisites:
                    if prereq.prerequisite_reward_id in item_reward_ids:
                        items_to_check.append(check_item.id)
                        break

@checklist_bp.route('/<int:checklist_id>/progress/<int:item_id>/toggle', methods=['POST'])
@login_required
@log_function_call
def toggle_progress(checklist_id, item_id):
    user_checklist = UserChecklist.query.filter_by(
        user_id=current_user.id,
        checklist_id=checklist_id
    ).first_or_404()
    
    # Get the item to check it exists and belongs to the checklist
    item = ChecklistItem.query.get_or_404(item_id)
    if item.checklist_id != checklist_id:
        abort(404)
    
    # Try to get existing progress entry, or create one if it doesn't exist
    # This handles cases where the database is missing user_progress entries
    # (e.g., from before the sync fix was implemented)
    progress = UserProgress.query.filter_by(
        user_checklist_id=user_checklist.id,
        item_id=item_id
    ).first()
    
    if not progress:
        # Create missing progress entry
        progress = UserProgress(
            user_checklist_id=user_checklist.id,
            item_id=item_id,
            completed=False
        )
        db.session.add(progress)
        db.session.flush()  # Ensure the progress entry is created before proceeding
    
    # If trying to mark as complete, check prerequisites
    if not progress.completed:
        prereqs_met, unmet_prereqs = item.are_prerequisites_met(user_checklist.id)
        if not prereqs_met:
            # Return error if prerequisites are not met
            if request.headers.get('Content-Type') == 'application/json' or request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'success': False, 
                    'error': 'Prerequisites not met',
                    'completed': False
                }), 400
            else:
                flash('Cannot complete this item - prerequisites not met!', 'error')
                return redirect(url_for('checklist.view', checklist_id=checklist_id))
    
    progress.completed = not progress.completed
    progress.completed_at = datetime.utcnow() if progress.completed else None
    db.session.commit()
    
    # If AJAX request, return JSON response with updated lock status
    if request.headers.get('Content-Type') == 'application/json' or request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # Find all items affected by this change using recursive chaining
        unlocked_items, locked_items = get_affected_items_recursive(
            checklist_id, user_checklist.id, item_id, progress.completed
        )
        
        return jsonify({
            'success': True, 
            'completed': progress.completed,
            'unlocked_items': unlocked_items,
            'locked_items': locked_items
        })
    
    # Otherwise, redirect (for backwards compatibility)
    return redirect(url_for('checklist.view', checklist_id=checklist_id))

@checklist_bp.route('/<int:checklist_id>/categories', methods=['GET'])
@log_function_call
def get_categories(checklist_id):
    """Get unique categories for a checklist."""
    checklist = Checklist.query.get_or_404(checklist_id)
    
    if not checklist.is_public and (not current_user.is_authenticated or checklist.creator_id != current_user.id):
        abort(403)
    
    categories = db.session.query(ChecklistItem.category).filter(
        ChecklistItem.checklist_id == checklist_id,
        ChecklistItem.category.isnot(None),
        ChecklistItem.category != ''
    ).distinct().all()
    
    category_list = [cat[0] for cat in categories]
    return jsonify({'categories': category_list})

@checklist_bp.route('/<int:checklist_id>/locations', methods=['GET'])
@log_function_call
def get_locations(checklist_id):
    """Get unique locations for a checklist."""
    checklist = Checklist.query.get_or_404(checklist_id)
    
    if not checklist.is_public and (not current_user.is_authenticated or checklist.creator_id != current_user.id):
        abort(403)
    
    locations = db.session.query(ChecklistItem.location).filter(
        ChecklistItem.checklist_id == checklist_id,
        ChecklistItem.location.isnot(None),
        ChecklistItem.location != ''
    ).distinct().all()
    
    location_list = [loc[0] for loc in locations]
    return jsonify({'locations': location_list})

@checklist_bp.route('/<int:checklist_id>/rewards', methods=['GET'])
@log_function_call
def get_rewards(checklist_id):
    """Get unique rewards for a checklist."""
    checklist = Checklist.query.get_or_404(checklist_id)
    
    if not checklist.is_public and (not current_user.is_authenticated or checklist.creator_id != current_user.id):
        abort(403)
    
    # Get all items for this checklist
    items = ChecklistItem.query.filter_by(checklist_id=checklist_id).all()
    
    # Get unique rewards across all items
    rewards_set = set()
    for item in items:
        for item_reward in item.rewards:
            rewards_set.add(item_reward.reward.name)
    
    reward_list = sorted(list(rewards_set))
    return jsonify({'rewards': reward_list})

@checklist_bp.route('/<int:checklist_id>/delete', methods=['POST'])
@login_required
@log_function_call
def delete(checklist_id):
    """Delete a checklist that the user created."""
    checklist = Checklist.query.get_or_404(checklist_id)
    
    # Only the creator can delete their checklist
    if checklist.creator_id != current_user.id:
        abort(403)
    
    game_id = checklist.game_id
    try:
        db.session.delete(checklist)
        db.session.commit()
        flash('Checklist deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while deleting the checklist.', 'error')
    
    # Redirect back to the game detail page
    return redirect(url_for('main.game_detail', game_id=game_id))

@checklist_bp.route('/<int:checklist_id>/delete-copy', methods=['POST'])
@login_required
@log_function_call
def delete_copy(checklist_id):
    """Delete a user's copy of a checklist (removes their progress)."""
    user_checklist = UserChecklist.query.filter_by(
        user_id=current_user.id,
        checklist_id=checklist_id
    ).first_or_404()
    
    checklist = Checklist.query.get_or_404(checklist_id)
    game_id = checklist.game_id
    
    try:
        db.session.delete(user_checklist)
        db.session.commit()
        flash('Checklist copy removed from your account!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while removing the checklist copy.', 'error')
    
    # Redirect back to the game detail page
    return redirect(url_for('main.game_detail', game_id=game_id))

@main_bp.route('/my-games')
@login_required
@log_function_call
def my_games():
    """Legacy route - redirect to games page."""
    return redirect(url_for('main.games'))

@main_bp.route('/select-game/<int:game_id>')
@login_required
@log_function_call
def select_game(game_id):
    """Legacy route - redirect to game detail page."""
    return redirect(url_for('main.game_detail', game_id=game_id))

@main_bp.route('/clear-game')
@login_required
@log_function_call
def clear_game():
    """Legacy route - redirect to games page."""
    return redirect(url_for('main.games'))

@main_bp.route('/my-checklists')
@login_required
@log_function_call
def my_checklists():
    """Legacy route - redirect to games page."""
    return redirect(url_for('main.games'))

@main_bp.route('/api/game-names')
@log_function_call
def get_game_names():
    """Get all unique game names for auto-complete."""
    games = Game.query.order_by(Game.name).all()
    game_names = [game.name for game in games]
    return jsonify({'game_names': game_names})

@main_bp.route('/api/categories/<int:game_id>')
@log_function_call
def get_categories_for_game(game_id):
    """Get unique categories for a specific game."""
    # Get all checklists for this game
    checklists = Checklist.query.filter_by(game_id=game_id).all()
    checklist_ids = [c.id for c in checklists]
    
    if not checklist_ids:
        return jsonify({'categories': []})
    
    # Get unique categories from all items in these checklists
    categories = db.session.query(ChecklistItem.category).filter(
        ChecklistItem.checklist_id.in_(checklist_ids),
        ChecklistItem.category.isnot(None),
        ChecklistItem.category != ''
    ).distinct().all()
    
    category_list = [cat[0] for cat in categories]
    return jsonify({'categories': category_list})

@main_bp.route('/api/locations/<int:game_id>')
@log_function_call
def get_locations_for_game(game_id):
    """Get unique locations for a specific game."""
    # Get all checklists for this game
    checklists = Checklist.query.filter_by(game_id=game_id).all()
    checklist_ids = [c.id for c in checklists]
    
    if not checklist_ids:
        return jsonify({'locations': []})
    
    # Get unique locations from all items in these checklists
    locations = db.session.query(ChecklistItem.location).filter(
        ChecklistItem.checklist_id.in_(checklist_ids),
        ChecklistItem.location.isnot(None),
        ChecklistItem.location != ''
    ).distinct().all()
    
    location_list = [loc[0] for loc in locations]
    return jsonify({'locations': location_list})
