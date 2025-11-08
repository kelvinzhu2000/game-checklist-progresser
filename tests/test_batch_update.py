import pytest
import sys
import os
import json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models import User, Game, Checklist, ChecklistItem


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


def test_batch_update_requires_login(client, app):
    """Test that batch update requires login."""
    with app.app_context():
        user = User(username='testuser', email='test@example.com')
        user.set_password('password123')
        db.session.add(user)
        
        game = Game(name='Test Game')
        db.session.add(game)
        db.session.flush()
        
        checklist = Checklist(
            title='Test Checklist',
            game_id=game.id,
            creator_id=user.id,
            is_public=True
        )
        db.session.add(checklist)
        db.session.commit()
        checklist_id = checklist.id
    
    # Try to batch update without login
    response = client.post(
        f'/checklist/{checklist_id}/batch-update',
        json={'title': 'Updated Title'},
        content_type='application/json'
    )
    assert response.status_code == 302  # Redirect to login


def test_batch_update_only_by_creator(client, app):
    """Test that only the creator can batch update a checklist."""
    with app.app_context():
        user1 = User(username='creator', email='creator@example.com')
        user1.set_password('password123')
        db.session.add(user1)
        
        user2 = User(username='other', email='other@example.com')
        user2.set_password('password123')
        db.session.add(user2)
        
        game = Game(name='Test Game')
        db.session.add(game)
        db.session.flush()
        
        checklist = Checklist(
            title='Test Checklist',
            game_id=game.id,
            creator_id=user1.id,
            is_public=True
        )
        db.session.add(checklist)
        db.session.commit()
        checklist_id = checklist.id
    
    # Login as non-creator
    client.post('/auth/login', data={
        'username': 'other',
        'password': 'password123'
    })
    
    # Try to batch update
    response = client.post(
        f'/checklist/{checklist_id}/batch-update',
        json={'title': 'Updated Title'},
        content_type='application/json'
    )
    assert response.status_code == 403  # Forbidden


def test_batch_update_checklist_metadata(client, app):
    """Test batch updating checklist metadata."""
    with app.app_context():
        user = User(username='testuser', email='test@example.com')
        user.set_password('password123')
        db.session.add(user)
        
        game = Game(name='Test Game')
        db.session.add(game)
        db.session.flush()
        
        checklist = Checklist(
            title='Original Title',
            game_id=game.id,
            description='Original description',
            creator_id=user.id,
            is_public=True
        )
        db.session.add(checklist)
        db.session.commit()
        checklist_id = checklist.id
    
    # Login
    client.post('/auth/login', data={
        'username': 'testuser',
        'password': 'password123'
    })
    
    # Batch update
    response = client.post(
        f'/checklist/{checklist_id}/batch-update',
        json={
            'title': 'Updated Title',
            'description': 'Updated description',
            'is_public': False,
            'items': []
        },
        content_type='application/json'
    )
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] is True
    
    # Verify changes
    with app.app_context():
        checklist = db.session.get(Checklist, checklist_id)
        assert checklist.title == 'Updated Title'
        assert checklist.description == 'Updated description'
        assert checklist.is_public is False


def test_batch_update_add_new_items(client, app):
    """Test adding new items via batch update."""
    with app.app_context():
        user = User(username='testuser', email='test@example.com')
        user.set_password('password123')
        db.session.add(user)
        
        game = Game(name='Test Game')
        db.session.add(game)
        db.session.flush()
        
        checklist = Checklist(
            title='Test Checklist',
            game_id=game.id,
            creator_id=user.id,
            is_public=True
        )
        db.session.add(checklist)
        db.session.commit()
        checklist_id = checklist.id
    
    # Login
    client.post('/auth/login', data={
        'username': 'testuser',
        'password': 'password123'
    })
    
    # Batch update with new items
    response = client.post(
        f'/checklist/{checklist_id}/batch-update',
        json={
            'title': 'Test Checklist',
            'items': [
                {'id': 'new', 'title': 'New Item 1', 'description': 'Description 1'},
                {'id': 'new', 'title': 'New Item 2', 'description': 'Description 2'}
            ]
        },
        content_type='application/json'
    )
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] is True
    
    # Verify items were added
    with app.app_context():
        items = ChecklistItem.query.filter_by(checklist_id=checklist_id).order_by(ChecklistItem.order).all()
        assert len(items) == 2
        assert items[0].title == 'New Item 1'
        assert items[0].description == 'Description 1'
        assert items[0].order == 1
        assert items[1].title == 'New Item 2'
        assert items[1].description == 'Description 2'
        assert items[1].order == 2


def test_batch_update_modify_existing_items(client, app):
    """Test modifying existing items via batch update."""
    with app.app_context():
        user = User(username='testuser', email='test@example.com')
        user.set_password('password123')
        db.session.add(user)
        
        game = Game(name='Test Game')
        db.session.add(game)
        db.session.flush()
        
        checklist = Checklist(
            title='Test Checklist',
            game_id=game.id,
            creator_id=user.id,
            is_public=True
        )
        db.session.add(checklist)
        db.session.flush()
        
        item1 = ChecklistItem(
            checklist_id=checklist.id,
            title='Original Item 1',
            description='Original description 1',
            order=1
        )
        item2 = ChecklistItem(
            checklist_id=checklist.id,
            title='Original Item 2',
            description='Original description 2',
            order=2
        )
        db.session.add(item1)
        db.session.add(item2)
        db.session.commit()
        checklist_id = checklist.id
        item1_id = item1.id
        item2_id = item2.id
    
    # Login
    client.post('/auth/login', data={
        'username': 'testuser',
        'password': 'password123'
    })
    
    # Batch update with modified items
    response = client.post(
        f'/checklist/{checklist_id}/batch-update',
        json={
            'title': 'Test Checklist',
            'items': [
                {'id': item1_id, 'title': 'Updated Item 1', 'description': 'Updated description 1'},
                {'id': item2_id, 'title': 'Updated Item 2', 'description': 'Updated description 2'}
            ]
        },
        content_type='application/json'
    )
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] is True
    
    # Verify items were updated
    with app.app_context():
        item1 = db.session.get(ChecklistItem, item1_id)
        item2 = db.session.get(ChecklistItem, item2_id)
        assert item1.title == 'Updated Item 1'
        assert item1.description == 'Updated description 1'
        assert item2.title == 'Updated Item 2'
        assert item2.description == 'Updated description 2'


def test_batch_update_delete_items(client, app):
    """Test deleting items via batch update."""
    with app.app_context():
        user = User(username='testuser', email='test@example.com')
        user.set_password('password123')
        db.session.add(user)
        
        game = Game(name='Test Game')
        db.session.add(game)
        db.session.flush()
        
        checklist = Checklist(
            title='Test Checklist',
            game_id=game.id,
            creator_id=user.id,
            is_public=True
        )
        db.session.add(checklist)
        db.session.flush()
        
        item1 = ChecklistItem(
            checklist_id=checklist.id,
            title='Item 1',
            order=1
        )
        item2 = ChecklistItem(
            checklist_id=checklist.id,
            title='Item 2',
            order=2
        )
        item3 = ChecklistItem(
            checklist_id=checklist.id,
            title='Item 3',
            order=3
        )
        db.session.add_all([item1, item2, item3])
        db.session.commit()
        checklist_id = checklist.id
        item1_id = item1.id
        item2_id = item2.id
        item3_id = item3.id
    
    # Login
    client.post('/auth/login', data={
        'username': 'testuser',
        'password': 'password123'
    })
    
    # Batch update - keep only item 1 and 3, delete item 2
    response = client.post(
        f'/checklist/{checklist_id}/batch-update',
        json={
            'title': 'Test Checklist',
            'items': [
                {'id': item1_id, 'title': 'Item 1'},
                {'id': item3_id, 'title': 'Item 3'}
            ],
            'deleted_items': [item2_id]
        },
        content_type='application/json'
    )
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] is True
    
    # Verify item 2 was deleted
    with app.app_context():
        items = ChecklistItem.query.filter_by(checklist_id=checklist_id).order_by(ChecklistItem.order).all()
        assert len(items) == 2
        assert items[0].id == item1_id
        assert items[1].id == item3_id
        
        # Verify item 2 no longer exists
        deleted_item = db.session.get(ChecklistItem, item2_id)
        assert deleted_item is None


def test_batch_update_reorder_items(client, app):
    """Test reordering items via batch update."""
    with app.app_context():
        user = User(username='testuser', email='test@example.com')
        user.set_password('password123')
        db.session.add(user)
        
        game = Game(name='Test Game')
        db.session.add(game)
        db.session.flush()
        
        checklist = Checklist(
            title='Test Checklist',
            game_id=game.id,
            creator_id=user.id,
            is_public=True
        )
        db.session.add(checklist)
        db.session.flush()
        
        item1 = ChecklistItem(checklist_id=checklist.id, title='Item 1', order=1)
        item2 = ChecklistItem(checklist_id=checklist.id, title='Item 2', order=2)
        item3 = ChecklistItem(checklist_id=checklist.id, title='Item 3', order=3)
        db.session.add_all([item1, item2, item3])
        db.session.commit()
        checklist_id = checklist.id
        item1_id = item1.id
        item2_id = item2.id
        item3_id = item3.id
    
    # Login
    client.post('/auth/login', data={
        'username': 'testuser',
        'password': 'password123'
    })
    
    # Batch update - reorder items (3, 1, 2)
    response = client.post(
        f'/checklist/{checklist_id}/batch-update',
        json={
            'title': 'Test Checklist',
            'items': [
                {'id': item3_id, 'title': 'Item 3'},
                {'id': item1_id, 'title': 'Item 1'},
                {'id': item2_id, 'title': 'Item 2'}
            ]
        },
        content_type='application/json'
    )
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] is True
    
    # Verify items were reordered
    with app.app_context():
        items = ChecklistItem.query.filter_by(checklist_id=checklist_id).order_by(ChecklistItem.order).all()
        assert len(items) == 3
        assert items[0].id == item3_id
        assert items[0].order == 1
        assert items[1].id == item1_id
        assert items[1].order == 2
        assert items[2].id == item2_id
        assert items[2].order == 3


def test_batch_update_combined_operations(client, app):
    """Test combining add, modify, delete, and reorder in one batch update."""
    with app.app_context():
        user = User(username='testuser', email='test@example.com')
        user.set_password('password123')
        db.session.add(user)
        
        game = Game(name='Test Game')
        db.session.add(game)
        db.session.flush()
        
        checklist = Checklist(
            title='Test Checklist',
            game_id=game.id,
            creator_id=user.id,
            is_public=True
        )
        db.session.add(checklist)
        db.session.flush()
        
        item1 = ChecklistItem(checklist_id=checklist.id, title='Item 1', order=1)
        item2 = ChecklistItem(checklist_id=checklist.id, title='Item 2', order=2)
        db.session.add_all([item1, item2])
        db.session.commit()
        checklist_id = checklist.id
        item1_id = item1.id
        item2_id = item2.id
    
    # Login
    client.post('/auth/login', data={
        'username': 'testuser',
        'password': 'password123'
    })
    
    # Batch update - modify item1, delete item2, add new item, reorder
    response = client.post(
        f'/checklist/{checklist_id}/batch-update',
        json={
            'title': 'Updated Checklist',
            'description': 'New description',
            'is_public': False,
            'items': [
                {'id': 'new', 'title': 'New Item', 'description': 'New item description'},
                {'id': item1_id, 'title': 'Modified Item 1', 'description': 'Modified description'}
            ],
            'deleted_items': [item2_id]
        },
        content_type='application/json'
    )
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] is True
    
    # Verify all changes
    with app.app_context():
        checklist = db.session.get(Checklist, checklist_id)
        assert checklist.title == 'Updated Checklist'
        assert checklist.description == 'New description'
        assert checklist.is_public is False
        
        items = ChecklistItem.query.filter_by(checklist_id=checklist_id).order_by(ChecklistItem.order).all()
        assert len(items) == 2
        
        # First item should be the new one
        assert items[0].title == 'New Item'
        assert items[0].description == 'New item description'
        assert items[0].order == 1
        
        # Second item should be modified item 1
        assert items[1].id == item1_id
        assert items[1].title == 'Modified Item 1'
        assert items[1].description == 'Modified description'
        assert items[1].order == 2
        
        # Item 2 should be deleted
        deleted_item = db.session.get(ChecklistItem, item2_id)
        assert deleted_item is None


def test_edit_page_shows_items(client, app):
    """Test that edit page displays existing items."""
    with app.app_context():
        user = User(username='testuser', email='test@example.com')
        user.set_password('password123')
        db.session.add(user)
        
        game = Game(name='Test Game')
        db.session.add(game)
        db.session.flush()
        
        checklist = Checklist(
            title='Test Checklist',
            game_id=game.id,
            creator_id=user.id,
            is_public=True
        )
        db.session.add(checklist)
        db.session.flush()
        
        item1 = ChecklistItem(checklist_id=checklist.id, title='Item 1', description='Description 1', order=1)
        item2 = ChecklistItem(checklist_id=checklist.id, title='Item 2', description='Description 2', order=2)
        db.session.add_all([item1, item2])
        db.session.commit()
        checklist_id = checklist.id
    
    # Login
    client.post('/auth/login', data={
        'username': 'testuser',
        'password': 'password123'
    })
    
    # Get edit page
    response = client.get(f'/checklist/{checklist_id}/edit')
    
    assert response.status_code == 200
    assert b'Item 1' in response.data
    assert b'Item 2' in response.data
    assert b'Description 1' in response.data
    assert b'Description 2' in response.data
    assert b'Checklist Items' in response.data
