from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import logging
import functools

logger = logging.getLogger(__name__)

def log_function_call(func):
    """Decorator to log function calls with parameters."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Get the instance (self) if it's a method
        if args and hasattr(args[0], '__class__'):
            class_name = args[0].__class__.__name__
            logger.info(f"{class_name}.{func.__name__} called with args={args[1:]}, kwargs={kwargs}")
        else:
            logger.info(f"{func.__name__} called with args={args}, kwargs={kwargs}")
        return func(*args, **kwargs)
    return wrapper

@login_manager.user_loader
@log_function_call
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
    
    @log_function_call
    def set_password(self, password):
        # Use pbkdf2:sha256 method for better compatibility across Python versions
        # Some Python builds (e.g., macOS Python 3.9) may not have scrypt available
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')
    
    @log_function_call
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
    
    @log_function_call
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
            
            # Type 2: Prerequisite reward - check if user has collected enough
            elif prereq.prerequisite_reward_id:
                if user_checklist_id:
                    # Get the user checklist to calculate reward tally
                    user_checklist = db.session.get(UserChecklist, user_checklist_id)
                    if user_checklist:
                        # Calculate the reward tally with filters
                        collected = user_checklist.get_reward_tally(
                            reward_id=prereq.prerequisite_reward_id,
                            location=prereq.reward_location,
                            category=prereq.reward_category
                        )
                        required = prereq.reward_amount or 1
                        
                        # Check if user has collected enough of this reward
                        if collected < required:
                            unmet.append(prereq)
                    else:
                        # Can't verify without user_checklist
                        unmet.append(prereq)
                else:
                    # Can't verify completion without user_checklist_id
                    unmet.append(prereq)
            
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
    
    @log_function_call
    def get_progress_percentage(self):
        total_items = ChecklistItem.query.filter_by(checklist_id=self.checklist_id).count()
        if total_items == 0:
            return 0
        completed_items = self.progress_items.filter_by(completed=True).count()
        return int((completed_items / total_items) * 100)
    
    @log_function_call
    def get_reward_tally(self, reward_id=None, location=None, category=None):
        """Calculate the total amount of a specific reward collected from completed items.
        
        Args:
            reward_id: The reward ID to tally. If None, returns a dict of all rewards.
            location: Optional location filter - only count rewards from items with this location
            category: Optional category filter - only count rewards from items with this category
            
        Returns:
            If reward_id is provided: int (total amount of that reward)
            If reward_id is None: dict {reward_id: total_amount, ...}
        """
        # Get all completed items for this user checklist
        completed_progress = self.progress_items.filter_by(completed=True).all()
        completed_item_ids = [p.item_id for p in completed_progress]
        
        if not completed_item_ids:
            return 0 if reward_id else {}
        
        # Query for items with rewards
        query = db.session.query(ChecklistItem, ItemReward).join(
            ItemReward, ChecklistItem.id == ItemReward.checklist_item_id
        ).filter(
            ChecklistItem.id.in_(completed_item_ids)
        )
        
        # Apply location filter if specified
        if location is not None:
            query = query.filter(ChecklistItem.location == location)
        
        # Apply category filter if specified
        if category is not None:
            query = query.filter(ChecklistItem.category == category)
        
        # Apply reward filter if specified
        if reward_id is not None:
            query = query.filter(ItemReward.reward_id == reward_id)
        
        results = query.all()
        
        if reward_id is not None:
            # Return total amount for specific reward
            return sum(item_reward.amount for _, item_reward in results)
        else:
            # Return dict of all rewards
            tally = {}
            for _, item_reward in results:
                if item_reward.reward_id not in tally:
                    tally[item_reward.reward_id] = 0
                tally[item_reward.reward_id] += item_reward.amount
            return tally
    
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
    reward_amount = db.Column(db.Integer, default=1, nullable=True)
    consumes_reward = db.Column(db.Boolean, default=False)
    reward_location = db.Column(db.String(100), nullable=True)  # Optional: filter reward by location
    reward_category = db.Column(db.String(100), nullable=True)  # Optional: filter reward by category
    
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
            filters = []
            if self.reward_location:
                filters.append(f'location={self.reward_location}')
            if self.reward_category:
                filters.append(f'category={self.reward_category}')
            filter_str = f' {" ".join(filters)}' if filters else ''
            return f'<ItemPrerequisite item_id={self.item_id} requires_reward={self.prerequisite_reward_id} amount={self.reward_amount} consumes={self.consumes_reward}{filter_str}>'
        else:
            return f'<ItemPrerequisite item_id={self.item_id} freeform="{self.freeform_text}">'
