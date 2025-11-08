import pytest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models import User, Game, Checklist, ChecklistItem, UserChecklist, UserProgress, Reward
import json

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

def test_reward_model_creation(app):
    """Test that Reward model can be created."""
    with app.app_context():
        reward = Reward(name='Gold Coin')
        db.session.add(reward)
        db.session.commit()
        
        retrieved_reward = Reward.query.filter_by(name='Gold Coin').first()
        assert retrieved_reward is not None
        assert retrieved_reward.name == 'Gold Coin'

def test_checklist_item_rewards_relationship(app):
    """Test many-to-many relationship between ChecklistItem and Reward."""
    with app.app_context():
        # Create a game
        game = Game(name='Test Game')
        db.session.add(game)
        db.session.commit()
        
        # Create a user
        user = User(username='testuser', email='test@example.com')
        user.set_password('password')
        db.session.add(user)
        db.session.commit()
        
        # Create a checklist
        checklist = Checklist(
            title='Test Checklist',
            game_id=game.id,
            creator_id=user.id,
            is_public=True
        )
        db.session.add(checklist)
        db.session.commit()
        
        # Create an item
        item = ChecklistItem(
            checklist_id=checklist.id,
            title='Test Item',
            order=1
        )
        db.session.add(item)
        db.session.commit()
        
        # Create rewards
        reward1 = Reward(name='Gold Coin')
        reward2 = Reward(name='Experience Points')
        db.session.add(reward1)
        db.session.add(reward2)
        db.session.commit()
        
        # Add rewards to item
        item.rewards.append(reward1)
        item.rewards.append(reward2)
        db.session.commit()
        
        # Verify relationships
        retrieved_item = ChecklistItem.query.get(item.id)
        assert retrieved_item.rewards.count() == 2
        reward_names = [r.name for r in retrieved_item.rewards.all()]
        assert 'Gold Coin' in reward_names
        assert 'Experience Points' in reward_names

def test_batch_update_with_rewards(auth_client, app):
    """Test batch updating items with rewards."""
    with app.app_context():
        # Create a game
        game = Game(name='Test Game')
        db.session.add(game)
        db.session.commit()
        
        # Get the user
        user = User.query.filter_by(username='testuser').first()
        
        # Create a checklist
        checklist = Checklist(
            title='Test Checklist',
            game_id=game.id,
            creator_id=user.id,
            is_public=True
        )
        db.session.add(checklist)
        db.session.commit()
        
        # Create an item
        item = ChecklistItem(
            checklist_id=checklist.id,
            title='Item 1',
            order=1
        )
        db.session.add(item)
        db.session.commit()
        
        checklist_id = checklist.id
        item_id = item.id
    
    # Update item via batch update with rewards
    update_data = {
        'title': 'Updated Checklist',
        'description': 'Updated description',
        'is_public': True,
        'items': [
            {
                'id': item_id,
                'title': 'Updated Item 1',
                'description': 'Desc 1',
                'category': 'Category A',
                'rewards': ['Gold Coin', 'Experience Points']
            }
        ],
        'deleted_items': []
    }
    
    response = auth_client.post(
        f'/checklist/{checklist_id}/batch-update',
        data=json.dumps(update_data),
        content_type='application/json'
    )
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] is True
    
    with app.app_context():
        item = ChecklistItem.query.get(item_id)
        assert item.rewards.count() == 2
        reward_names = [r.name for r in item.rewards.all()]
        assert 'Gold Coin' in reward_names
        assert 'Experience Points' in reward_names

def test_add_new_item_with_rewards_via_batch_update(auth_client, app):
    """Test adding a new item with rewards via batch update."""
    with app.app_context():
        # Create a game
        game = Game(name='Test Game')
        db.session.add(game)
        db.session.commit()
        
        # Get the user
        user = User.query.filter_by(username='testuser').first()
        
        # Create a checklist
        checklist = Checklist(
            title='Test Checklist',
            game_id=game.id,
            creator_id=user.id,
            is_public=True
        )
        db.session.add(checklist)
        db.session.commit()
        checklist_id = checklist.id
    
    # Add a new item via batch update with rewards
    update_data = {
        'title': 'Test Checklist',
        'description': '',
        'is_public': True,
        'items': [
            {
                'id': 'new',
                'title': 'New Item',
                'description': 'New Description',
                'category': 'New Category',
                'rewards': ['Diamond', 'Rare Item']
            }
        ],
        'deleted_items': []
    }
    
    response = auth_client.post(
        f'/checklist/{checklist_id}/batch-update',
        data=json.dumps(update_data),
        content_type='application/json'
    )
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] is True
    
    with app.app_context():
        item = ChecklistItem.query.filter_by(title='New Item').first()
        assert item is not None
        assert item.rewards.count() == 2
        reward_names = [r.name for r in item.rewards.all()]
        assert 'Diamond' in reward_names
        assert 'Rare Item' in reward_names

def test_get_rewards_endpoint(auth_client, app):
    """Test the API endpoint that returns unique rewards for a checklist."""
    with app.app_context():
        # Create a game
        game = Game(name='Test Game')
        db.session.add(game)
        db.session.commit()
        
        # Get the user
        user = User.query.filter_by(username='testuser').first()
        
        # Create a checklist
        checklist = Checklist(
            title='Test Checklist',
            game_id=game.id,
            creator_id=user.id,
            is_public=True
        )
        db.session.add(checklist)
        db.session.commit()
        
        # Create rewards
        reward1 = Reward(name='Gold Coin')
        reward2 = Reward(name='Experience Points')
        reward3 = Reward(name='Diamond')
        db.session.add(reward1)
        db.session.add(reward2)
        db.session.add(reward3)
        db.session.commit()
        
        # Create items with various rewards
        item1 = ChecklistItem(
            checklist_id=checklist.id,
            title='Item 1',
            order=1
        )
        item1.rewards.append(reward1)
        item1.rewards.append(reward2)
        
        item2 = ChecklistItem(
            checklist_id=checklist.id,
            title='Item 2',
            order=2
        )
        item2.rewards.append(reward2)
        item2.rewards.append(reward3)
        
        item3 = ChecklistItem(
            checklist_id=checklist.id,
            title='Item 3',
            order=3
        )
        # No rewards
        
        db.session.add(item1)
        db.session.add(item2)
        db.session.add(item3)
        db.session.commit()
        
        checklist_id = checklist.id
    
    # Get rewards
    response = auth_client.get(f'/checklist/{checklist_id}/rewards')
    assert response.status_code == 200
    
    data = json.loads(response.data)
    rewards = data['rewards']
    
    # Should return all unique rewards
    assert len(rewards) == 3
    assert 'Gold Coin' in rewards
    assert 'Experience Points' in rewards
    assert 'Diamond' in rewards

def test_view_checklist_with_rewards(auth_client, app):
    """Test viewing a checklist that has items with rewards."""
    with app.app_context():
        # Create a game
        game = Game(name='Test Game')
        db.session.add(game)
        db.session.commit()
        
        # Get the user
        user = User.query.filter_by(username='testuser').first()
        
        # Create a checklist
        checklist = Checklist(
            title='Test Checklist',
            game_id=game.id,
            creator_id=user.id,
            is_public=True
        )
        db.session.add(checklist)
        db.session.commit()
        
        # Create rewards
        reward1 = Reward(name='Gold Coin')
        reward2 = Reward(name='Experience')
        db.session.add(reward1)
        db.session.add(reward2)
        db.session.commit()
        
        # Create items with rewards
        item1 = ChecklistItem(
            checklist_id=checklist.id,
            title='Item 1',
            order=1
        )
        item1.rewards.append(reward1)
        
        item2 = ChecklistItem(
            checklist_id=checklist.id,
            title='Item 2',
            order=2
        )
        item2.rewards.append(reward2)
        
        db.session.add(item1)
        db.session.add(item2)
        db.session.commit()
        checklist_id = checklist.id
    
    # View the checklist
    response = auth_client.get(f'/checklist/{checklist_id}')
    assert response.status_code == 200
    
    # Check that reward badges are shown
    assert b'Gold Coin' in response.data
    assert b'Experience' in response.data
    assert b'item-reward-badge' in response.data

def test_item_without_rewards(auth_client, app):
    """Test that items without rewards still work correctly."""
    with app.app_context():
        # Create a game
        game = Game(name='Test Game')
        db.session.add(game)
        db.session.commit()
        
        # Get the user
        user = User.query.filter_by(username='testuser').first()
        
        # Create a checklist
        checklist = Checklist(
            title='Test Checklist',
            game_id=game.id,
            creator_id=user.id,
            is_public=True
        )
        db.session.add(checklist)
        db.session.commit()
        
        # Create an item without rewards
        item = ChecklistItem(
            checklist_id=checklist.id,
            title='Item without rewards',
            order=1
        )
        db.session.add(item)
        db.session.commit()
        checklist_id = checklist.id
        item_id = item.id
    
    # View the checklist
    response = auth_client.get(f'/checklist/{checklist_id}')
    assert response.status_code == 200
    assert b'Item without rewards' in response.data
    
    # Verify item has no rewards
    with app.app_context():
        item = ChecklistItem.query.get(item_id)
        assert item.rewards.count() == 0

def test_update_rewards_removes_old_rewards(auth_client, app):
    """Test that updating rewards removes old rewards and adds new ones."""
    with app.app_context():
        # Create a game
        game = Game(name='Test Game')
        db.session.add(game)
        db.session.commit()
        
        # Get the user
        user = User.query.filter_by(username='testuser').first()
        
        # Create a checklist
        checklist = Checklist(
            title='Test Checklist',
            game_id=game.id,
            creator_id=user.id,
            is_public=True
        )
        db.session.add(checklist)
        db.session.commit()
        
        # Create rewards
        reward1 = Reward(name='Old Reward')
        db.session.add(reward1)
        db.session.commit()
        
        # Create an item with old reward
        item = ChecklistItem(
            checklist_id=checklist.id,
            title='Item 1',
            order=1
        )
        item.rewards.append(reward1)
        db.session.add(item)
        db.session.commit()
        
        checklist_id = checklist.id
        item_id = item.id
    
    # Update item with new rewards
    update_data = {
        'title': 'Test Checklist',
        'description': '',
        'is_public': True,
        'items': [
            {
                'id': item_id,
                'title': 'Item 1',
                'description': '',
                'category': '',
                'rewards': ['New Reward 1', 'New Reward 2']
            }
        ],
        'deleted_items': []
    }
    
    response = auth_client.post(
        f'/checklist/{checklist_id}/batch-update',
        data=json.dumps(update_data),
        content_type='application/json'
    )
    
    assert response.status_code == 200
    
    with app.app_context():
        item = ChecklistItem.query.get(item_id)
        assert item.rewards.count() == 2
        reward_names = [r.name for r in item.rewards.all()]
        assert 'New Reward 1' in reward_names
        assert 'New Reward 2' in reward_names
        assert 'Old Reward' not in reward_names

def test_reward_reuse_across_items(auth_client, app):
    """Test that the same reward can be used for multiple items."""
    with app.app_context():
        # Create a game
        game = Game(name='Test Game')
        db.session.add(game)
        db.session.commit()
        
        # Get the user
        user = User.query.filter_by(username='testuser').first()
        
        # Create a checklist
        checklist = Checklist(
            title='Test Checklist',
            game_id=game.id,
            creator_id=user.id,
            is_public=True
        )
        db.session.add(checklist)
        db.session.commit()
        checklist_id = checklist.id
    
    # Add two items with the same reward
    update_data = {
        'title': 'Test Checklist',
        'description': '',
        'is_public': True,
        'items': [
            {
                'id': 'new',
                'title': 'Item 1',
                'description': '',
                'category': '',
                'rewards': ['Shared Reward']
            },
            {
                'id': 'new',
                'title': 'Item 2',
                'description': '',
                'category': '',
                'rewards': ['Shared Reward']
            }
        ],
        'deleted_items': []
    }
    
    response = auth_client.post(
        f'/checklist/{checklist_id}/batch-update',
        data=json.dumps(update_data),
        content_type='application/json'
    )
    
    assert response.status_code == 200
    
    with app.app_context():
        # Should only create one reward object
        rewards = Reward.query.filter_by(name='Shared Reward').all()
        assert len(rewards) == 1
        
        # Both items should have the same reward
        items = ChecklistItem.query.filter_by(checklist_id=checklist_id).all()
        assert len(items) == 2
        for item in items:
            assert item.rewards.count() == 1
            assert item.rewards.first().name == 'Shared Reward'
