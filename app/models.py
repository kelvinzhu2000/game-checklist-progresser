from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

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
        # Use pbkdf2:sha256 method for better compatibility across Python versions
        # Some Python builds (e.g., macOS Python 3.9) may not have scrypt available
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'

class Game(db.Model):
    __tablename__ = 'games'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), unique=True, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    checklists = db.relationship('Checklist', backref='game', lazy='dynamic',
                                cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Game {self.name}>'

class Checklist(db.Model):
    __tablename__ = 'checklists'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    game_id = db.Column(db.Integer, db.ForeignKey('games.id'), nullable=False, index=True)
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
        return f'<Checklist {self.title} for {self.game.name}>'

class ChecklistItem(db.Model):
    __tablename__ = 'checklist_items'
    
    id = db.Column(db.Integer, primary_key=True)
    checklist_id = db.Column(db.Integer, db.ForeignKey('checklists.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    location = db.Column(db.String(100))
    category = db.Column(db.String(100))
    order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    rewards = db.relationship('ItemReward', cascade='all, delete-orphan')
    prerequisites = db.relationship('ItemPrerequisite', 
                                   foreign_keys='ItemPrerequisite.item_id',
                                   cascade='all, delete-orphan')
    
    def are_prerequisites_met(self, user_checklist_id=None):
        """Check if all prerequisites are met for this item.
        
        Args:
            user_checklist_id: Optional user_checklist_id to check item completion status
            
        Returns:
            tuple: (bool, list) - (are_met, list_of_unmet_prerequisites)
        """
        unmet = []
        
        for prereq in self.prerequisites:
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
                    # Can't verify completion without user_checklist_id
                    unmet.append(prereq)
            
            # Type 2: Prerequisite reward (consumes_reward is informational only)
            # Freeform rewards are informational - we can't check if they're "met"
            # They're just displayed to the user
            elif prereq.prerequisite_reward_id:
                # Reward prerequisites are informational, don't block completion
                pass
            
            # Type 3: Freeform text (informational only)
            elif prereq.freeform_text:
                # Freeform prerequisites are informational, don't block completion
                pass
        
        return (len(unmet) == 0, unmet)
    
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

class Reward(db.Model):
    __tablename__ = 'rewards'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Reward {self.name}>'

class ItemReward(db.Model):
    """Association object for ChecklistItem and Reward with amount."""
    __tablename__ = 'checklist_item_rewards'
    
    checklist_item_id = db.Column(db.Integer, db.ForeignKey('checklist_items.id'), primary_key=True)
    reward_id = db.Column(db.Integer, db.ForeignKey('rewards.id'), primary_key=True)
    amount = db.Column(db.Integer, default=1, nullable=False)
    
    # Relationships
    reward = db.relationship('Reward')
    
    def __repr__(self):
        return f'<ItemReward item_id={self.checklist_item_id} reward_id={self.reward_id} amount={self.amount}>'

class ItemPrerequisite(db.Model):
    """Prerequisites for checklist items.
    
    Supports three types of prerequisites:
    1. Other checklist items (prerequisite_item_id)
    2. Rewards (prerequisite_reward_id with consumes_reward flag)
    3. Freeform text (freeform_text)
    """
    __tablename__ = 'item_prerequisites'
    
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('checklist_items.id'), nullable=False)
    
    # Type 1: Prerequisite is another checklist item
    prerequisite_item_id = db.Column(db.Integer, db.ForeignKey('checklist_items.id'), nullable=True)
    
    # Type 2: Prerequisite is a reward
    prerequisite_reward_id = db.Column(db.Integer, db.ForeignKey('rewards.id'), nullable=True)
    consumes_reward = db.Column(db.Boolean, default=False)
    
    # Type 3: Freeform text prerequisite
    freeform_text = db.Column(db.String(200), nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    prerequisite_item = db.relationship('ChecklistItem', 
                                       foreign_keys=[prerequisite_item_id],
                                       backref='dependent_items')
    prerequisite_reward = db.relationship('Reward')
    
    def __repr__(self):
        if self.prerequisite_item_id:
            return f'<ItemPrerequisite item_id={self.item_id} requires_item={self.prerequisite_item_id}>'
        elif self.prerequisite_reward_id:
            return f'<ItemPrerequisite item_id={self.item_id} requires_reward={self.prerequisite_reward_id} consumes={self.consumes_reward}>'
        else:
            return f'<ItemPrerequisite item_id={self.item_id} freeform="{self.freeform_text}">'
