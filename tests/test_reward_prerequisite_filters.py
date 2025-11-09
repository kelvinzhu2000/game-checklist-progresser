"""Tests for reward prerequisite location and category filtering feature."""

import pytest
import json
from app import create_app, db
from app.models import User, Game, Checklist, ChecklistItem, Reward, ItemPrerequisite, ItemReward
from config import TestingConfig


@pytest.fixture
def app():
    """Create application for testing."""
    app = create_app()
    app.config.from_object(TestingConfig)
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def authenticated_user(client, app):
    """Create and authenticate a test user."""
    with app.app_context():
        user = User(username='testuser', email='test@example.com')
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
        user_id = user.id
    
    # Log in
    client.post('/auth/login', data={
        'username': 'testuser',
        'password': 'password123'
    }, follow_redirects=True)
    
    return user_id


def test_reward_prerequisite_with_location(app, authenticated_user):
    """Test adding a reward prerequisite with location filter."""
    with app.app_context():
        # Create a game
        game = Game(name='Test Game')
        db.session.add(game)
        db.session.commit()
        
        # Create a checklist
        checklist = Checklist(
            title='Test Checklist',
            game_id=game.id,
            creator_id=authenticated_user,
            is_public=True
        )
        db.session.add(checklist)
        db.session.commit()
        
        # Create an item with reward prerequisite that has location
        item = ChecklistItem(
            checklist_id=checklist.id,
            title='Item 1',
            description='Test item',
            order=1
        )
        db.session.add(item)
        db.session.flush()
        
        # Create a reward
        reward = Reward(name='Gold Coin')
        db.session.add(reward)
        db.session.flush()
        
        # Create prerequisite with location filter
        prereq = ItemPrerequisite(
            item_id=item.id,
            prerequisite_reward_id=reward.id,
            reward_amount=10,
            consumes_reward=False,
            reward_location='Castle',
            reward_category=None
        )
        db.session.add(prereq)
        db.session.commit()
        
        # Verify the prerequisite was created with location
        saved_prereq = ItemPrerequisite.query.filter_by(item_id=item.id).first()
        assert saved_prereq is not None
        assert saved_prereq.prerequisite_reward_id == reward.id
        assert saved_prereq.reward_amount == 10
        assert saved_prereq.reward_location == 'Castle'
        assert saved_prereq.reward_category is None


def test_reward_prerequisite_with_category(app, authenticated_user):
    """Test adding a reward prerequisite with category filter."""
    with app.app_context():
        # Create a game
        game = Game(name='Test Game')
        db.session.add(game)
        db.session.commit()
        
        # Create a checklist
        checklist = Checklist(
            title='Test Checklist',
            game_id=game.id,
            creator_id=authenticated_user,
            is_public=True
        )
        db.session.add(checklist)
        db.session.commit()
        
        # Create an item with reward prerequisite that has category
        item = ChecklistItem(
            checklist_id=checklist.id,
            title='Item 1',
            description='Test item',
            order=1
        )
        db.session.add(item)
        db.session.flush()
        
        # Create a reward
        reward = Reward(name='Ruby')
        db.session.add(reward)
        db.session.flush()
        
        # Create prerequisite with category filter
        prereq = ItemPrerequisite(
            item_id=item.id,
            prerequisite_reward_id=reward.id,
            reward_amount=5,
            consumes_reward=True,
            reward_location=None,
            reward_category='Gems'
        )
        db.session.add(prereq)
        db.session.commit()
        
        # Verify the prerequisite was created with category
        saved_prereq = ItemPrerequisite.query.filter_by(item_id=item.id).first()
        assert saved_prereq is not None
        assert saved_prereq.prerequisite_reward_id == reward.id
        assert saved_prereq.reward_amount == 5
        assert saved_prereq.reward_location is None
        assert saved_prereq.reward_category == 'Gems'
        assert saved_prereq.consumes_reward is True


def test_reward_prerequisite_with_both_filters(app, authenticated_user):
    """Test adding a reward prerequisite with both location and category filters."""
    with app.app_context():
        # Create a game
        game = Game(name='Test Game')
        db.session.add(game)
        db.session.commit()
        
        # Create a checklist
        checklist = Checklist(
            title='Test Checklist',
            game_id=game.id,
            creator_id=authenticated_user,
            is_public=True
        )
        db.session.add(checklist)
        db.session.commit()
        
        # Create an item with reward prerequisite that has both location and category
        item = ChecklistItem(
            checklist_id=checklist.id,
            title='Item 1',
            description='Test item',
            order=1
        )
        db.session.add(item)
        db.session.flush()
        
        # Create a reward
        reward = Reward(name='Star')
        db.session.add(reward)
        db.session.flush()
        
        # Create prerequisite with both filters
        prereq = ItemPrerequisite(
            item_id=item.id,
            prerequisite_reward_id=reward.id,
            reward_amount=3,
            consumes_reward=False,
            reward_location='Tower',
            reward_category='Special'
        )
        db.session.add(prereq)
        db.session.commit()
        
        # Verify the prerequisite was created with both filters
        saved_prereq = ItemPrerequisite.query.filter_by(item_id=item.id).first()
        assert saved_prereq is not None
        assert saved_prereq.prerequisite_reward_id == reward.id
        assert saved_prereq.reward_amount == 3
        assert saved_prereq.reward_location == 'Tower'
        assert saved_prereq.reward_category == 'Special'


def test_batch_update_with_location_category_filters(client, app, authenticated_user):
    """Test batch update with reward prerequisites that have location and category filters."""
    with app.app_context():
        # Create a game
        game = Game(name='Test Game')
        db.session.add(game)
        db.session.commit()
        game_id = game.id
        
        # Create a checklist
        checklist = Checklist(
            title='Test Checklist',
            game_id=game_id,
            creator_id=authenticated_user,
            is_public=True
        )
        db.session.add(checklist)
        db.session.commit()
        checklist_id = checklist.id
        
        # Create an item
        item = ChecklistItem(
            checklist_id=checklist_id,
            title='Item 1',
            description='Test item',
            order=1
        )
        db.session.add(item)
        db.session.commit()
        item_id = item.id
    
    # Update the item with prerequisites including location and category
    data = {
        'title': 'Test Checklist',
        'description': 'Test description',
        'is_public': True,
        'items': [
            {
                'id': item_id,
                'title': 'Updated Item 1',
                'description': 'Updated description',
                'location': 'Forest',
                'category': 'Quest',
                'rewards': [],
                'prerequisites': [
                    {
                        'type': 'reward',
                        'reward_name': 'Magic Key',
                        'reward_amount': 2,
                        'consumes_reward': False,
                        'reward_location': 'Dungeon',
                        'reward_category': 'Key Items'
                    }
                ]
            }
        ],
        'deleted_items': []
    }
    
    response = client.post(
        f'/checklist/{checklist_id}/batch-update',
        data=json.dumps(data),
        content_type='application/json'
    )
    
    assert response.status_code == 200
    result = json.loads(response.data)
    assert result['success'] is True
    
    # Verify the prerequisite was saved with location and category
    with app.app_context():
        item = ChecklistItem.query.get(item_id)
        assert len(item.prerequisites) == 1
        prereq = item.prerequisites[0]
        assert prereq.prerequisite_reward is not None
        assert prereq.prerequisite_reward.name == 'Magic Key'
        assert prereq.reward_amount == 2
        assert prereq.consumes_reward is False
        assert prereq.reward_location == 'Dungeon'
        assert prereq.reward_category == 'Key Items'


def test_batch_update_with_new_item_and_filters(client, app, authenticated_user):
    """Test batch update adding a new item with reward prerequisites that have filters."""
    with app.app_context():
        # Create a game
        game = Game(name='Test Game')
        db.session.add(game)
        db.session.commit()
        game_id = game.id
        
        # Create a checklist
        checklist = Checklist(
            title='Test Checklist',
            game_id=game_id,
            creator_id=authenticated_user,
            is_public=True
        )
        db.session.add(checklist)
        db.session.commit()
        checklist_id = checklist.id
    
    # Add a new item with prerequisites including location and category
    data = {
        'title': 'Test Checklist',
        'description': 'Test description',
        'is_public': True,
        'items': [
            {
                'id': 'new',
                'title': 'New Item',
                'description': 'New item description',
                'location': 'Cave',
                'category': 'Boss',
                'rewards': [],
                'prerequisites': [
                    {
                        'type': 'reward',
                        'reward_name': 'Fire Crystal',
                        'reward_amount': 1,
                        'consumes_reward': True,
                        'reward_location': 'Volcano',
                        'reward_category': 'Crystals'
                    }
                ]
            }
        ],
        'deleted_items': []
    }
    
    response = client.post(
        f'/checklist/{checklist_id}/batch-update',
        data=json.dumps(data),
        content_type='application/json'
    )
    
    assert response.status_code == 200
    result = json.loads(response.data)
    assert result['success'] is True
    
    # Verify the new item was created with the prerequisite
    with app.app_context():
        items = ChecklistItem.query.filter_by(checklist_id=checklist_id).all()
        assert len(items) == 1
        item = items[0]
        assert item.title == 'New Item'
        assert len(item.prerequisites) == 1
        prereq = item.prerequisites[0]
        assert prereq.prerequisite_reward is not None
        assert prereq.prerequisite_reward.name == 'Fire Crystal'
        assert prereq.reward_amount == 1
        assert prereq.consumes_reward is True
        assert prereq.reward_location == 'Volcano'
        assert prereq.reward_category == 'Crystals'


def test_batch_update_without_filters(client, app, authenticated_user):
    """Test batch update with reward prerequisites without filters (backward compatibility)."""
    with app.app_context():
        # Create a game
        game = Game(name='Test Game')
        db.session.add(game)
        db.session.commit()
        game_id = game.id
        
        # Create a checklist
        checklist = Checklist(
            title='Test Checklist',
            game_id=game_id,
            creator_id=authenticated_user,
            is_public=True
        )
        db.session.add(checklist)
        db.session.commit()
        checklist_id = checklist.id
    
    # Add a new item with prerequisites without location/category
    data = {
        'title': 'Test Checklist',
        'description': 'Test description',
        'is_public': True,
        'items': [
            {
                'id': 'new',
                'title': 'New Item',
                'description': 'New item description',
                'location': '',
                'category': '',
                'rewards': [],
                'prerequisites': [
                    {
                        'type': 'reward',
                        'reward_name': 'Basic Coin',
                        'reward_amount': 5,
                        'consumes_reward': False
                    }
                ]
            }
        ],
        'deleted_items': []
    }
    
    response = client.post(
        f'/checklist/{checklist_id}/batch-update',
        data=json.dumps(data),
        content_type='application/json'
    )
    
    assert response.status_code == 200
    result = json.loads(response.data)
    assert result['success'] is True
    
    # Verify the prerequisite was created without filters
    with app.app_context():
        items = ChecklistItem.query.filter_by(checklist_id=checklist_id).all()
        assert len(items) == 1
        item = items[0]
        assert len(item.prerequisites) == 1
        prereq = item.prerequisites[0]
        assert prereq.prerequisite_reward is not None
        assert prereq.prerequisite_reward.name == 'Basic Coin'
        assert prereq.reward_amount == 5
        assert prereq.consumes_reward is False
        assert prereq.reward_location is None
        assert prereq.reward_category is None
