import pytest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models import User, Game, Checklist, ChecklistItem, UserChecklist, UserProgress, Reward, ItemReward

@pytest.fixture
def app():
    """Create and configure a test app instance."""
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    """Create a test client."""
    return app.test_client()

@pytest.fixture
def auth_client(client, app):
    """Create an authenticated test client."""
    with app.app_context():
        # Create a test user
        user = User(username='testuser', email='test@example.com')
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
    
    # Log in
    client.post('/auth/login', data={
        'username': 'testuser',
        'password': 'password123'
    })
    
    return client

def test_reward_tally_displays_on_user_checklist(auth_client, app):
    """Test that reward tally section displays when user has copied a checklist."""
    with app.app_context():
        # Create game
        game = Game(name='Test Game')
        db.session.add(game)
        db.session.commit()
        
        # Get user
        user = User.query.filter_by(username='testuser').first()
        
        # Create checklist
        checklist = Checklist(
            title='Test Checklist',
            game_id=game.id,
            creator_id=user.id,
            is_public=True
        )
        db.session.add(checklist)
        db.session.commit()
        
        # Create rewards
        gold = Reward(name='Gold')
        gems = Reward(name='Gems')
        db.session.add(gold)
        db.session.add(gems)
        db.session.commit()
        
        # Create items with rewards
        item1 = ChecklistItem(
            checklist_id=checklist.id,
            title='Item 1',
            category='Quest',
            order=1
        )
        db.session.add(item1)
        db.session.flush()
        
        item_reward1 = ItemReward(checklist_item_id=item1.id, reward_id=gold.id, amount=10)
        db.session.add(item_reward1)
        
        item2 = ChecklistItem(
            checklist_id=checklist.id,
            title='Item 2',
            category='Quest',
            order=2
        )
        db.session.add(item2)
        db.session.flush()
        
        item_reward2 = ItemReward(checklist_item_id=item2.id, reward_id=gems.id, amount=5)
        db.session.add(item_reward2)
        db.session.commit()
        
        # Copy checklist to user
        user_checklist = UserChecklist(user_id=user.id, checklist_id=checklist.id)
        db.session.add(user_checklist)
        db.session.commit()
        
        # Add progress
        progress1 = UserProgress(
            user_checklist_id=user_checklist.id,
            item_id=item1.id,
            completed=True
        )
        progress2 = UserProgress(
            user_checklist_id=user_checklist.id,
            item_id=item2.id,
            completed=False
        )
        db.session.add(progress1)
        db.session.add(progress2)
        db.session.commit()
        
        checklist_id = checklist.id
    
    # View the checklist
    response = auth_client.get(f'/checklist/{checklist_id}')
    assert response.status_code == 200
    
    # Check that reward tally section is present
    assert b'Reward Tally' in response.data
    assert b'All Items' in response.data
    assert b'Filtered Items' in response.data
    
    # Check for reward display elements
    assert b'total-rewards-all' in response.data
    assert b'total-rewards-filtered' in response.data

def test_reward_tally_data_attributes(auth_client, app):
    """Test that items have correct data attributes for reward tally calculation."""
    with app.app_context():
        # Create game
        game = Game(name='Test Game')
        db.session.add(game)
        db.session.commit()
        
        # Get user
        user = User.query.filter_by(username='testuser').first()
        
        # Create checklist
        checklist = Checklist(
            title='Test Checklist',
            game_id=game.id,
            creator_id=user.id,
            is_public=True
        )
        db.session.add(checklist)
        db.session.commit()
        
        # Create reward
        gold = Reward(name='Gold Coin')
        db.session.add(gold)
        db.session.commit()
        
        # Create item with reward
        item = ChecklistItem(
            checklist_id=checklist.id,
            title='Test Item',
            order=1
        )
        db.session.add(item)
        db.session.flush()
        
        item_reward = ItemReward(checklist_item_id=item.id, reward_id=gold.id, amount=15)
        db.session.add(item_reward)
        db.session.commit()
        
        # Copy checklist to user
        user_checklist = UserChecklist(user_id=user.id, checklist_id=checklist.id)
        db.session.add(user_checklist)
        db.session.commit()
        
        # Add progress
        progress = UserProgress(
            user_checklist_id=user_checklist.id,
            item_id=item.id,
            completed=True
        )
        db.session.add(progress)
        db.session.commit()
        
        checklist_id = checklist.id
    
    # View the checklist
    response = auth_client.get(f'/checklist/{checklist_id}')
    assert response.status_code == 200
    
    # Check data attributes
    assert b'data-reward-details="Gold Coin:15"' in response.data
    assert b'data-completed="true"' in response.data

def test_reward_tally_not_displayed_for_non_user_checklist(client, app):
    """Test that reward tally is not shown when user hasn't copied the checklist."""
    with app.app_context():
        # Create a user who owns the checklist
        owner = User(username='owner', email='owner@example.com')
        owner.set_password('password')
        db.session.add(owner)
        db.session.commit()
        
        # Create game
        game = Game(name='Test Game')
        db.session.add(game)
        db.session.commit()
        
        # Create checklist
        checklist = Checklist(
            title='Test Checklist',
            game_id=game.id,
            creator_id=owner.id,
            is_public=True
        )
        db.session.add(checklist)
        db.session.commit()
        
        checklist_id = checklist.id
    
    # View the checklist without logging in
    response = client.get(f'/checklist/{checklist_id}')
    assert response.status_code == 200
    
    # Reward tally div should not be present (checked via the div with id)
    assert b'id="reward-tally"' not in response.data

def test_multiple_rewards_per_item(auth_client, app):
    """Test that items with multiple rewards are handled correctly."""
    with app.app_context():
        # Create game
        game = Game(name='Test Game')
        db.session.add(game)
        db.session.commit()
        
        # Get user
        user = User.query.filter_by(username='testuser').first()
        
        # Create checklist
        checklist = Checklist(
            title='Test Checklist',
            game_id=game.id,
            creator_id=user.id,
            is_public=True
        )
        db.session.add(checklist)
        db.session.commit()
        
        # Create rewards
        gold = Reward(name='Gold')
        gems = Reward(name='Gems')
        xp = Reward(name='XP')
        db.session.add_all([gold, gems, xp])
        db.session.commit()
        
        # Create item with multiple rewards
        item = ChecklistItem(
            checklist_id=checklist.id,
            title='Multi-reward Item',
            order=1
        )
        db.session.add(item)
        db.session.flush()
        
        item_reward1 = ItemReward(checklist_item_id=item.id, reward_id=gold.id, amount=100)
        item_reward2 = ItemReward(checklist_item_id=item.id, reward_id=gems.id, amount=50)
        item_reward3 = ItemReward(checklist_item_id=item.id, reward_id=xp.id, amount=1000)
        db.session.add_all([item_reward1, item_reward2, item_reward3])
        db.session.commit()
        
        # Copy checklist to user
        user_checklist = UserChecklist(user_id=user.id, checklist_id=checklist.id)
        db.session.add(user_checklist)
        db.session.commit()
        
        # Add progress
        progress = UserProgress(
            user_checklist_id=user_checklist.id,
            item_id=item.id,
            completed=False
        )
        db.session.add(progress)
        db.session.commit()
        
        checklist_id = checklist.id
    
    # View the checklist
    response = auth_client.get(f'/checklist/{checklist_id}')
    assert response.status_code == 200
    
    # Check that all rewards are in data attributes
    response_text = response.data.decode('utf-8')
    assert 'Gold:100' in response_text
    assert 'Gems:50' in response_text
    assert 'XP:1000' in response_text

def test_reward_tally_javascript_functions(auth_client, app):
    """Test that JavaScript functions for reward tally are included."""
    with app.app_context():
        # Create minimal setup
        game = Game(name='Test Game')
        db.session.add(game)
        db.session.commit()
        
        user = User.query.filter_by(username='testuser').first()
        
        checklist = Checklist(
            title='Test Checklist',
            game_id=game.id,
            creator_id=user.id,
            is_public=True
        )
        db.session.add(checklist)
        db.session.commit()
        
        # Copy checklist
        user_checklist = UserChecklist(user_id=user.id, checklist_id=checklist.id)
        db.session.add(user_checklist)
        db.session.commit()
        
        checklist_id = checklist.id
    
    # View the checklist
    response = auth_client.get(f'/checklist/{checklist_id}')
    assert response.status_code == 200
    
    # Check for JavaScript functions
    assert b'calculateRewardTotals' in response.data
    assert b'updateRewardTally' in response.data
