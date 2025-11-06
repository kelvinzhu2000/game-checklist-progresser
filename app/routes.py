from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, session
from flask_login import login_user, logout_user, current_user, login_required
from urllib.parse import urlparse
from app import db
from app.models import User, Checklist, ChecklistItem, UserChecklist, UserProgress
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
        # Set the game context to the checklist's game
        set_selected_game(checklist.game_name)
        return redirect(url_for('main.my_checklists'))
    
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
    
    # Set the game context to the copied checklist's game
    set_selected_game(checklist.game_name)
    
    flash('Checklist copied to your account!', 'success')
    return redirect(url_for('main.my_checklists'))

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

@checklist_bp.route('/<int:checklist_id>/delete-copy', methods=['POST'])
@login_required
def delete_copy(checklist_id):
    """Delete a user's copy of a checklist (removes their progress)."""
    user_checklist = UserChecklist.query.filter_by(
        user_id=current_user.id,
        checklist_id=checklist_id
    ).first_or_404()
    
    checklist = Checklist.query.get_or_404(checklist_id)
    game_name = checklist.game_name
    
    try:
        db.session.delete(user_checklist)
        db.session.commit()
        flash('Checklist copy removed from your account!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while removing the checklist copy.', 'error')
    
    # Redirect back to my checklists with the same game selected
    set_selected_game(game_name)
    return redirect(url_for('main.my_checklists'))

@main_bp.route('/my-games')
@login_required
def my_games():
    """Display list of games the user has checklists for."""
    # Get games from created checklists
    created_games = db.session.query(Checklist.game_name).filter_by(
        creator_id=current_user.id
    ).distinct().all()
    
    # Get games from copied checklists
    copied_games = db.session.query(Checklist.game_name).join(
        UserChecklist, Checklist.id == UserChecklist.checklist_id
    ).filter(
        UserChecklist.user_id == current_user.id
    ).distinct().all()
    
    # Combine and deduplicate
    all_games = set()
    for game in created_games:
        all_games.add(game[0])
    for game in copied_games:
        all_games.add(game[0])
    
    # Sort games alphabetically
    games = sorted(list(all_games))
    
    # Get checklist count per game
    game_stats = {}
    for game in games:
        created_count = current_user.created_checklists.filter_by(game_name=game).count()
        copied_count = db.session.query(UserChecklist).join(
            Checklist, Checklist.id == UserChecklist.checklist_id
        ).filter(
            UserChecklist.user_id == current_user.id,
            Checklist.game_name == game
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
    
    # Filter checklists by selected game
    created = current_user.created_checklists.filter_by(
        game_name=selected_game
    ).order_by(Checklist.created_at.desc()).all()
    
    copied = db.session.query(UserChecklist).join(
        Checklist, Checklist.id == UserChecklist.checklist_id
    ).filter(
        UserChecklist.user_id == current_user.id,
        Checklist.game_name == selected_game
    ).all()
    
    return render_template('my_checklists.html', created=created, copied=copied, selected_game=selected_game)
