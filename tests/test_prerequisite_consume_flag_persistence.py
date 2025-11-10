import pytest
import sys
import os
import json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models import User, Game, Checklist, ChecklistItem, Reward, ItemPrerequisite


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


def test_prerequisite_consume_flag_persists_on_edit_without_changes(client, app):
    """
    Test that when editing a checklist without making changes to prerequisites,
    the consumes_reward flag remains set to True if it was originally True.
    
    This is a regression test for the bug where editing a checklist and clicking
    "Save Changes" without making any changes would reset the consumes_reward flag to False.
    """
    with app.app_context():
        # Create test user
        user = User(username='testuser', email='test@example.com')
        user.set_password('password123')
        db.session.add(user)
        
        # Create game
        game = Game(name='Test Game')
        db.session.add(game)
        db.session.flush()
        
        # Create checklist
        checklist = Checklist(
            title='Test Checklist',
            game_id=game.id,
            creator_id=user.id,
            is_public=True
        )
        db.session.add(checklist)
        db.session.flush()
        
        # Create reward
        reward = Reward(name='Gold Coin')
        db.session.add(reward)
        db.session.flush()
        
        # Create item with prerequisite that consumes the reward
        item1 = ChecklistItem(
            checklist_id=checklist.id,
            title='Item 1',
            description='First item',
            order=1
        )
        db.session.add(item1)
        db.session.flush()
        
        # Create prerequisite that consumes the reward
        prereq = ItemPrerequisite(
            item_id=item1.id,
            prerequisite_reward_id=reward.id,
            reward_amount=5,
            consumes_reward=True  # This should persist
        )
        db.session.add(prereq)
        db.session.commit()
        
        checklist_id = checklist.id
        item1_id = item1.id
        prereq_id = prereq.id
        reward_id = reward.id
    
    # Login
    client.post('/auth/login', data={
        'username': 'testuser',
        'password': 'password123'
    })
    
    # Verify initial state
    with app.app_context():
        prereq = db.session.get(ItemPrerequisite, prereq_id)
        assert prereq.consumes_reward is True, "Initial consumes_reward should be True"
        assert prereq.reward_amount == 5
    
    # Simulate editing the checklist without making changes
    # This simulates the user opening the edit page and clicking "Save Changes"
    # without modifying any prerequisites
    with app.app_context():
        item1 = db.session.get(ChecklistItem, item1_id)
        reward = db.session.get(Reward, reward_id)
        
        # Collect the current item data (this is what the JavaScript would send)
        items_data = [{
            'id': item1_id,
            'title': item1.title,
            'description': item1.description,
            'location': item1.location or '',
            'category': item1.category or '',
            'rewards': [],
            'prerequisites': [{
                'type': 'reward',
                'reward_name': reward.name,
                'reward_amount': 5,
                'consumes_reward': True,  # JavaScript correctly reads this as true
                'reward_location': '',
                'reward_category': ''
            }]
        }]
    
    # Batch update with the same data (no changes)
    response = client.post(
        f'/checklist/{checklist_id}/batch-update',
        json={
            'title': 'Test Checklist',
            'description': '',
            'is_public': True,
            'items': items_data,
            'deleted_items': []
        },
        content_type='application/json'
    )
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] is True
    
    # Verify that consumes_reward flag is still True
    with app.app_context():
        prereq = ItemPrerequisite.query.filter_by(item_id=item1_id).first()
        assert prereq is not None, "Prerequisite should still exist"
        assert prereq.prerequisite_reward_id == reward_id
        assert prereq.reward_amount == 5
        assert prereq.consumes_reward is True, "consumes_reward should still be True after edit"


def test_prerequisite_consume_flag_can_be_toggled(client, app):
    """
    Test that the consumes_reward flag can be intentionally changed from True to False
    and from False to True through the edit interface.
    """
    with app.app_context():
        # Create test user
        user = User(username='testuser', email='test@example.com')
        user.set_password('password123')
        db.session.add(user)
        
        # Create game
        game = Game(name='Test Game')
        db.session.add(game)
        db.session.flush()
        
        # Create checklist
        checklist = Checklist(
            title='Test Checklist',
            game_id=game.id,
            creator_id=user.id,
            is_public=True
        )
        db.session.add(checklist)
        db.session.flush()
        
        # Create reward
        reward = Reward(name='Gold Coin')
        db.session.add(reward)
        db.session.flush()
        
        # Create item with prerequisite that does NOT consume the reward
        item1 = ChecklistItem(
            checklist_id=checklist.id,
            title='Item 1',
            description='First item',
            order=1
        )
        db.session.add(item1)
        db.session.flush()
        
        # Create prerequisite that does NOT consume the reward
        prereq = ItemPrerequisite(
            item_id=item1.id,
            prerequisite_reward_id=reward.id,
            reward_amount=5,
            consumes_reward=False  # Initially False
        )
        db.session.add(prereq)
        db.session.commit()
        
        checklist_id = checklist.id
        item1_id = item1.id
        reward_id = reward.id
    
    # Login
    client.post('/auth/login', data={
        'username': 'testuser',
        'password': 'password123'
    })
    
    # Verify initial state
    with app.app_context():
        prereq = ItemPrerequisite.query.filter_by(item_id=item1_id).first()
        assert prereq.consumes_reward is False, "Initial consumes_reward should be False"
    
    # Update to set consumes_reward to True
    response = client.post(
        f'/checklist/{checklist_id}/batch-update',
        json={
            'title': 'Test Checklist',
            'description': '',
            'is_public': True,
            'items': [{
                'id': item1_id,
                'title': 'Item 1',
                'description': 'First item',
                'location': '',
                'category': '',
                'rewards': [],
                'prerequisites': [{
                    'type': 'reward',
                    'reward_name': 'Gold Coin',
                    'reward_amount': 5,
                    'consumes_reward': True,  # Changed to True
                    'reward_location': '',
                    'reward_category': ''
                }]
            }],
            'deleted_items': []
        },
        content_type='application/json'
    )
    
    assert response.status_code == 200
    
    # Verify that consumes_reward is now True
    with app.app_context():
        prereq = ItemPrerequisite.query.filter_by(item_id=item1_id).first()
        assert prereq.consumes_reward is True, "consumes_reward should be True after update"
    
    # Update to set consumes_reward back to False
    response = client.post(
        f'/checklist/{checklist_id}/batch-update',
        json={
            'title': 'Test Checklist',
            'description': '',
            'is_public': True,
            'items': [{
                'id': item1_id,
                'title': 'Item 1',
                'description': 'First item',
                'location': '',
                'category': '',
                'rewards': [],
                'prerequisites': [{
                    'type': 'reward',
                    'reward_name': 'Gold Coin',
                    'reward_amount': 5,
                    'consumes_reward': False,  # Changed back to False
                    'reward_location': '',
                    'reward_category': ''
                }]
            }],
            'deleted_items': []
        },
        content_type='application/json'
    )
    
    assert response.status_code == 200
    
    # Verify that consumes_reward is now False
    with app.app_context():
        prereq = ItemPrerequisite.query.filter_by(item_id=item1_id).first()
        assert prereq.consumes_reward is False, "consumes_reward should be False after second update"
