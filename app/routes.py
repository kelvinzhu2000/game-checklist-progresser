from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_user, logout_user, current_user, login_required
from app import db
from app.models import User, Checklist, ChecklistItem, UserChecklist, UserProgress
from app.forms import RegistrationForm, LoginForm, ChecklistForm, ChecklistItemForm
from datetime import datetime

main_bp = Blueprint('main', __name__)
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')
checklist_bp = Blueprint('checklist', __name__, url_prefix='/checklist')

@main_bp.route('/')
def index():
    public_checklists = Checklist.query.filter_by(is_public=True).order_by(Checklist.created_at.desc()).limit(10).all()
    return render_template('index.html', checklists=public_checklists)

@main_bp.route('/browse')
def browse():
    page = request.args.get('page', 1, type=int)
    game = request.args.get('game', '', type=str)
    
    query = Checklist.query.filter_by(is_public=True)
    if game:
        query = query.filter(Checklist.game_name.ilike(f'%{game}%'))
    
    pagination = query.order_by(Checklist.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('browse.html', pagination=pagination, game=game)

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
            return redirect(next_page) if next_page else redirect(url_for('main.index'))
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
    form = ChecklistForm()
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
        flash('Checklist created successfully!', 'success')
        return redirect(url_for('checklist.view', checklist_id=checklist.id))
    
    return render_template('create_checklist.html', form=form)

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

@main_bp.route('/my-checklists')
@login_required
def my_checklists():
    created = current_user.created_checklists.order_by(Checklist.created_at.desc()).all()
    copied = current_user.user_checklists.all()
    
    return render_template('my_checklists.html', created=created, copied=copied)
