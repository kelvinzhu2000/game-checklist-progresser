from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, session
from flask_login import login_user, logout_user, current_user, login_required
from urllib.parse import urlparse
from app import db
from app.models import User, Checklist, ChecklistItem, UserProgress
from app.forms import RegistrationForm, LoginForm, ChecklistForm, ChecklistItemForm
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

@main_bp.route('/browse')
def browse():
    """Browse public checklists by game."""
    # Get all unique games from public checklists
    games_query = db.session.query(
        Checklist.game_name,
        func.count(Checklist.id).label('checklist_count')
    ).filter_by(is_public=True).group_by(Checklist.game_name).order_by(Checklist.game_name)
    
    games = games_query.all()
    
    return render_template('browse.html', games=games)

@main_bp.route('/browse/<game_name>')
def browse_game(game_name):
    """Browse checklists for a specific game."""
    page = request.args.get('page', 1, type=int)
    
    query = Checklist.query.filter_by(is_public=True, game_name=game_name)
    
    pagination = query.order_by(Checklist.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('browse_game.html', pagination=pagination, game_name=game_name)

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
@login_required
def create():
    selected_game = get_selected_game()
    
    form = ChecklistForm()
    
    # Pre-populate game_name if a game is selected
    if request.method == 'GET' and selected_game:
        form.game_name.data = selected_game
    
    if form.validate_on_submit():
        checklist = Checklist(
            title=form.title.data,
            game_name=form.game_name.data,
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
        
        # Update selected game if it changed
        if form.game_name.data != selected_game:
            set_selected_game(form.game_name.data)
        
        return redirect(url_for('checklist.view', checklist_id=checklist.id))
    
    return render_template('create_checklist.html', form=form, selected_game=selected_game)

@checklist_bp.route('/<int:checklist_id>')
def view(checklist_id):
    checklist = Checklist.query.get_or_404(checklist_id)
    
    # Check permissions - user must be creator or checklist must be public/parent is public
    if not checklist.is_public and (not current_user.is_authenticated or checklist.creator_id != current_user.id):
        abort(403)
    
    items = checklist.items.all()
    progress = {}
    
    if current_user.is_authenticated and checklist.creator_id == current_user.id:
        # If this is the user's own checklist (copy), show their progress
        for item in items:
            prog = UserProgress.query.filter_by(
                checklist_id=checklist_id,
                item_id=item.id
            ).first()
            progress[item.id] = prog.completed if prog else False
    
    return render_template('view_checklist.html', checklist=checklist, items=items, progress=progress)

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
    parent_checklist = Checklist.query.get_or_404(checklist_id)
    
    if not parent_checklist.is_public and parent_checklist.creator_id != current_user.id:
        abort(403)
    
    # Check if user already has a copy
    existing = Checklist.query.filter_by(
        creator_id=current_user.id,
        parent_id=checklist_id
    ).first()
    
    if existing:
        flash('You already have a copy of this checklist!', 'warning')
        set_selected_game(parent_checklist.game_name)
        return redirect(url_for('main.my_checklists'))
    
    # Create a new checklist as a copy
    new_checklist = Checklist(
        title=parent_checklist.title,
        game_name=parent_checklist.game_name,
        description=parent_checklist.description,
        creator_id=current_user.id,
        is_public=False,  # Copies are private by default
        parent_id=checklist_id
    )
    db.session.add(new_checklist)
    db.session.flush()  # Get the ID
    
    # Copy all items from parent checklist
    for parent_item in parent_checklist.items.all():
        new_item = ChecklistItem(
            checklist_id=new_checklist.id,
            title=parent_item.title,
            description=parent_item.description,
            order=parent_item.order
        )
        db.session.add(new_item)
    
    db.session.flush()  # Ensure items are created
    
    # Create progress records for all items (initially uncompleted)
    for item in new_checklist.items.all():
        progress = UserProgress(
            checklist_id=new_checklist.id,
            item_id=item.id,
            completed=False
        )
        db.session.add(progress)
    
    db.session.commit()
    
    set_selected_game(parent_checklist.game_name)
    flash('Checklist copied to your account!', 'success')
    return redirect(url_for('main.my_checklists'))

@checklist_bp.route('/<int:checklist_id>/progress/<int:item_id>/toggle', methods=['POST'])
@login_required
def toggle_progress(checklist_id, item_id):
    checklist = Checklist.query.get_or_404(checklist_id)
    
    # Only the creator can toggle progress on their own checklist
    if checklist.creator_id != current_user.id:
        abort(403)
    
    progress = UserProgress.query.filter_by(
        checklist_id=checklist_id,
        item_id=item_id
    ).first_or_404()
    
    progress.completed = not progress.completed
    progress.completed_at = datetime.utcnow() if progress.completed else None
    db.session.commit()
    
    return redirect(url_for('checklist.view', checklist_id=checklist_id))

@checklist_bp.route('/<int:checklist_id>/delete', methods=['POST'])
@login_required
def delete(checklist_id):
    """Delete a checklist that the user created/owns."""
    checklist = Checklist.query.get_or_404(checklist_id)
    
    # Only the creator can delete their checklist
    if checklist.creator_id != current_user.id:
        abort(403)
    
    game_name = checklist.game_name
    try:
        db.session.delete(checklist)
        db.session.commit()
        flash('Checklist deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while deleting the checklist.', 'error')
    
    # Redirect back to my checklists with the same game selected
    set_selected_game(game_name)
    return redirect(url_for('main.my_checklists'))

@main_bp.route('/my-games')
@login_required
def my_games():
    """Display list of games the user has checklists for."""
    # Get all games from user's checklists (both original and copies)
    games_query = db.session.query(Checklist.game_name).filter_by(
        creator_id=current_user.id
    ).distinct().all()
    
    # Extract game names and sort alphabetically
    games = sorted([game[0] for game in games_query])
    
    # Get checklist count per game
    game_stats = {}
    for game in games:
        # Count original checklists (no parent)
        created_count = current_user.checklists.filter_by(
            game_name=game,
            parent_id=None
        ).count()
        # Count copied checklists (has parent)
        copied_count = current_user.checklists.filter(
            Checklist.game_name == game,
            Checklist.parent_id != None
        ).count()
        game_stats[game] = {'created': created_count, 'copied': copied_count}
    
    selected_game = get_selected_game()
    
    return render_template('my_games.html', games=games, game_stats=game_stats, selected_game=selected_game)

@main_bp.route('/select-game/<game_name>')
@login_required
def select_game(game_name):
    """Select a game to view checklists for."""
    set_selected_game(game_name)
    flash(f'Selected game: {game_name}', 'success')
    return redirect(url_for('main.my_checklists'))

@main_bp.route('/clear-game')
@login_required
def clear_game():
    """Clear the selected game."""
    clear_selected_game()
    flash('Game selection cleared. Viewing all games.', 'info')
    return redirect(url_for('main.my_games'))

@main_bp.route('/my-checklists')
@login_required
def my_checklists():
    selected_game = get_selected_game()
    
    if not selected_game:
        # If no game selected, redirect to game selection
        return redirect(url_for('main.my_games'))
    
    # Get original checklists (no parent) for selected game
    created = current_user.checklists.filter_by(
        game_name=selected_game,
        parent_id=None
    ).order_by(Checklist.created_at.desc()).all()
    
    # Get copied checklists (has parent) for selected game
    copied = current_user.checklists.filter(
        Checklist.game_name == selected_game,
        Checklist.parent_id != None
    ).order_by(Checklist.created_at.desc()).all()
    
    return render_template('my_checklists.html', created=created, copied=copied, selected_game=selected_game)
