from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, session
from flask_login import login_user, logout_user, current_user, login_required
from urllib.parse import urlparse
from app import db
from app.models import User, Game, Checklist, ChecklistItem, UserChecklist, UserProgress
from app.forms import RegistrationForm, LoginForm, ChecklistForm, ChecklistItemForm, GameForm, ChecklistEditForm
from app.ai_service import generate_checklist_items
from datetime import datetime
from sqlalchemy import func

main_bp = Blueprint('main', __name__)
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')
checklist_bp = Blueprint('checklist', __name__, url_prefix='/checklist')

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

def get_selected_game():
    """Get the currently selected game from session."""
    return session.get('selected_game')

def set_selected_game(game_name):
    """Set the currently selected game in session."""
    session['selected_game'] = game_name

def clear_selected_game():
    """Clear the currently selected game from session."""
    session.pop('selected_game', None)

@main_bp.route('/')
def index():
    public_checklists = Checklist.query.filter_by(is_public=True).order_by(Checklist.created_at.desc()).limit(10).all()
    return render_template('index.html', checklists=public_checklists)

@main_bp.route('/games')
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
def browse():
    """Legacy route - redirect to games page."""
    return redirect(url_for('main.games'))

@main_bp.route('/browse/<int:game_id>')
def browse_game(game_id):
    """Legacy route - redirect to game detail page."""
    return redirect(url_for('main.game_detail', game_id=game_id))

@auth_bp.route('/register', methods=['GET', 'POST'])
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
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))

@checklist_bp.route('/create', methods=['GET', 'POST'])
@checklist_bp.route('/create/<int:game_id>', methods=['GET', 'POST'])
@login_required
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
def view(checklist_id):
    checklist = Checklist.query.get_or_404(checklist_id)
    
    if not checklist.is_public and (not current_user.is_authenticated or checklist.creator_id != current_user.id):
        abort(403)
    
    items = checklist.items.all()
    user_copy = None
    progress = {}
    
    if current_user.is_authenticated:
        user_copy = UserChecklist.query.filter_by(
            user_id=current_user.id,
            checklist_id=checklist_id
        ).first()
        
        if user_copy:
            for item in items:
                prog = UserProgress.query.filter_by(
                    user_checklist_id=user_copy.id,
                    item_id=item.id
                ).first()
                progress[item.id] = prog.completed if prog else False
    
    return render_template('view_checklist.html', checklist=checklist, items=items, 
                         user_copy=user_copy, progress=progress)

@checklist_bp.route('/<int:checklist_id>/edit', methods=['GET', 'POST'])
@login_required
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
    
    return render_template('edit_checklist.html', form=form, checklist=checklist)

@checklist_bp.route('/<int:checklist_id>/add_item', methods=['GET', 'POST'])
@login_required
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
            order=max_order + 1
        )
        db.session.add(item)
        db.session.commit()
        flash('Item added successfully!', 'success')
        return redirect(url_for('checklist.view', checklist_id=checklist_id))
    
    return render_template('add_item.html', form=form, checklist=checklist)

@checklist_bp.route('/<int:checklist_id>/copy', methods=['POST'])
@login_required
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

@checklist_bp.route('/<int:checklist_id>/progress/<int:item_id>/toggle', methods=['POST'])
@login_required
def toggle_progress(checklist_id, item_id):
    user_checklist = UserChecklist.query.filter_by(
        user_id=current_user.id,
        checklist_id=checklist_id
    ).first_or_404()
    
    progress = UserProgress.query.filter_by(
        user_checklist_id=user_checklist.id,
        item_id=item_id
    ).first_or_404()
    
    progress.completed = not progress.completed
    progress.completed_at = datetime.utcnow() if progress.completed else None
    db.session.commit()
    
    return redirect(url_for('checklist.view', checklist_id=checklist_id))

@checklist_bp.route('/<int:checklist_id>/delete', methods=['POST'])
@login_required
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
def my_games():
    """Legacy route - redirect to games page."""
    return redirect(url_for('main.games'))

@main_bp.route('/select-game/<int:game_id>')
@login_required
def select_game(game_id):
    """Legacy route - redirect to game detail page."""
    return redirect(url_for('main.game_detail', game_id=game_id))

@main_bp.route('/clear-game')
@login_required
def clear_game():
    """Legacy route - redirect to games page."""
    return redirect(url_for('main.games'))

@main_bp.route('/my-checklists')
@login_required
def my_checklists():
    """Legacy route - redirect to games page."""
    return redirect(url_for('main.games'))
