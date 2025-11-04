from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    created_checklists = db.relationship('Checklist', backref='creator', lazy='dynamic', 
                                        foreign_keys='Checklist.creator_id')
    user_checklists = db.relationship('UserChecklist', backref='user', lazy='dynamic',
                                     cascade='all, delete-orphan')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'

class Checklist(db.Model):
    __tablename__ = 'checklists'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    game_name = db.Column(db.String(200), nullable=False, index=True)
    description = db.Column(db.Text)
    creator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    is_public = db.Column(db.Boolean, default=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    items = db.relationship('ChecklistItem', backref='checklist', lazy='dynamic',
                           cascade='all, delete-orphan', order_by='ChecklistItem.order')
    user_copies = db.relationship('UserChecklist', backref='original_checklist', lazy='dynamic',
                                 cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Checklist {self.title} for {self.game_name}>'

class ChecklistItem(db.Model):
    __tablename__ = 'checklist_items'
    
    id = db.Column(db.Integer, primary_key=True)
    checklist_id = db.Column(db.Integer, db.ForeignKey('checklists.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<ChecklistItem {self.title}>'

class UserChecklist(db.Model):
    __tablename__ = 'user_checklists'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    checklist_id = db.Column(db.Integer, db.ForeignKey('checklists.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    progress_items = db.relationship('UserProgress', backref='user_checklist', lazy='dynamic',
                                    cascade='all, delete-orphan')
    
    def get_progress_percentage(self):
        total_items = ChecklistItem.query.filter_by(checklist_id=self.checklist_id).count()
        if total_items == 0:
            return 0
        completed_items = self.progress_items.filter_by(completed=True).count()
        return int((completed_items / total_items) * 100)
    
    def __repr__(self):
        return f'<UserChecklist user_id={self.user_id} checklist_id={self.checklist_id}>'

class UserProgress(db.Model):
    __tablename__ = 'user_progress'
    
    id = db.Column(db.Integer, primary_key=True)
    user_checklist_id = db.Column(db.Integer, db.ForeignKey('user_checklists.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('checklist_items.id'), nullable=False)
    completed = db.Column(db.Boolean, default=False)
    completed_at = db.Column(db.DateTime)
    
    # Relationship to the item
    item = db.relationship('ChecklistItem', backref='progress_records')
    
    def __repr__(self):
        return f'<UserProgress item_id={self.item_id} completed={self.completed}>'
