import pytest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models import User, Game, Checklist, ChecklistItem, UserChecklist, UserProgress


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


def test_delete_item_requires_login(client, app):
    """Test that deleting an item requires login."""
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
        
        item = ChecklistItem(
            checklist_id=checklist.id,
            title='Test Item',
            order=1
        )
        db.session.add(item)
        db.session.commit()
        checklist_id = checklist.id
        item_id = item.id
    
    # Try to delete item without login
    response = client.post(f'/checklist/{checklist_id}/item/{item_id}/delete')
    assert response.status_code == 302  # Redirect to login


def test_delete_item_only_by_creator(client, app):
    """Test that only the creator can delete items from their checklist."""
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
        db.session.flush()
        
        item = ChecklistItem(
            checklist_id=checklist.id,
            title='Test Item',
            order=1
        )
        db.session.add(item)
        db.session.commit()
        checklist_id = checklist.id
        item_id = item.id
    
    # Login as non-creator
    client.post('/auth/login', data={
        'username': 'other',
        'password': 'password123'
    })
    
    # Try to delete item
    response = client.post(f'/checklist/{checklist_id}/item/{item_id}/delete')
    assert response.status_code == 403  # Forbidden
    
    # Verify item still exists
    with app.app_context():
        item = db.session.get(ChecklistItem, item_id)
        assert item is not None


def test_delete_item_success(client, app):
    """Test successfully deleting a checklist item."""
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
        db.session.add_all([item1, item2])
        db.session.commit()
        checklist_id = checklist.id
        item1_id = item1.id
        item2_id = item2.id
    
    # Login as creator
    client.post('/auth/login', data={
        'username': 'testuser',
        'password': 'password123'
    })
    
    # Delete item1
    response = client.post(f'/checklist/{checklist_id}/item/{item1_id}/delete', follow_redirects=True)
    assert response.status_code == 200
    assert b'Item deleted successfully!' in response.data
    
    # Verify item1 is deleted but item2 remains
    with app.app_context():
        deleted_item = db.session.get(ChecklistItem, item1_id)
        assert deleted_item is None
        
        remaining_item = db.session.get(ChecklistItem, item2_id)
        assert remaining_item is not None
        assert remaining_item.title == 'Item 2'


def test_delete_item_removes_progress(client, app):
    """Test that deleting an item also removes associated progress records."""
    with app.app_context():
        user = User(username='testuser', email='test@example.com')
        user.set_password('password123')
        db.session.add(user)
        db.session.flush()
        
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
        
        item = ChecklistItem(
            checklist_id=checklist.id,
            title='Test Item',
            order=1
        )
        db.session.add(item)
        db.session.flush()
        
        # Create a user checklist copy with progress
        user_checklist = UserChecklist(
            user_id=user.id,
            checklist_id=checklist.id
        )
        db.session.add(user_checklist)
        db.session.flush()
        
        progress = UserProgress(
            user_checklist_id=user_checklist.id,
            item_id=item.id,
            completed=True
        )
        db.session.add(progress)
        db.session.commit()
        
        checklist_id = checklist.id
        item_id = item.id
        progress_id = progress.id
    
    # Login as creator
    client.post('/auth/login', data={
        'username': 'testuser',
        'password': 'password123'
    })
    
    # Delete item
    response = client.post(f'/checklist/{checklist_id}/item/{item_id}/delete', follow_redirects=True)
    assert response.status_code == 200
    
    # Verify both item and progress are deleted
    with app.app_context():
        deleted_item = db.session.get(ChecklistItem, item_id)
        assert deleted_item is None
        
        deleted_progress = db.session.get(UserProgress, progress_id)
        assert deleted_progress is None


def test_delete_item_wrong_checklist(client, app):
    """Test that we can't delete an item using wrong checklist ID."""
    with app.app_context():
        user = User(username='testuser', email='test@example.com')
        user.set_password('password123')
        db.session.add(user)
        
        game = Game(name='Test Game')
        db.session.add(game)
        db.session.flush()
        
        checklist1 = Checklist(
            title='Checklist 1',
            game_id=game.id,
            creator_id=user.id,
            is_public=True
        )
        checklist2 = Checklist(
            title='Checklist 2',
            game_id=game.id,
            creator_id=user.id,
            is_public=True
        )
        db.session.add_all([checklist1, checklist2])
        db.session.flush()
        
        item1 = ChecklistItem(
            checklist_id=checklist1.id,
            title='Item 1',
            order=1
        )
        db.session.add(item1)
        db.session.commit()
        
        checklist2_id = checklist2.id
        item1_id = item1.id
    
    # Login as creator
    client.post('/auth/login', data={
        'username': 'testuser',
        'password': 'password123'
    })
    
    # Try to delete item1 using checklist2's ID
    response = client.post(f'/checklist/{checklist2_id}/item/{item1_id}/delete')
    assert response.status_code == 404  # Not found
    
    # Verify item still exists
    with app.app_context():
        item = db.session.get(ChecklistItem, item1_id)
        assert item is not None


def test_delete_nonexistent_item(client, app):
    """Test deleting a non-existent item returns 404."""
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
    
    # Try to delete non-existent item
    response = client.post(f'/checklist/{checklist_id}/item/99999/delete')
    assert response.status_code == 404


def test_delete_item_multiple_users_with_progress(client, app):
    """Test that deleting an item removes progress for all users who copied the checklist."""
    with app.app_context():
        user1 = User(username='creator', email='creator@example.com')
        user1.set_password('password123')
        user2 = User(username='user2', email='user2@example.com')
        user2.set_password('password123')
        db.session.add_all([user1, user2])
        db.session.flush()
        
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
        db.session.flush()
        
        item = ChecklistItem(
            checklist_id=checklist.id,
            title='Test Item',
            order=1
        )
        db.session.add(item)
        db.session.flush()
        
        # Both users copy the checklist
        user_checklist1 = UserChecklist(user_id=user1.id, checklist_id=checklist.id)
        user_checklist2 = UserChecklist(user_id=user2.id, checklist_id=checklist.id)
        db.session.add_all([user_checklist1, user_checklist2])
        db.session.flush()
        
        # Both users have progress on the item
        progress1 = UserProgress(user_checklist_id=user_checklist1.id, item_id=item.id, completed=True)
        progress2 = UserProgress(user_checklist_id=user_checklist2.id, item_id=item.id, completed=False)
        db.session.add_all([progress1, progress2])
        db.session.commit()
        
        checklist_id = checklist.id
        item_id = item.id
        progress1_id = progress1.id
        progress2_id = progress2.id
    
    # Login as creator
    client.post('/auth/login', data={
        'username': 'creator',
        'password': 'password123'
    })
    
    # Delete item
    response = client.post(f'/checklist/{checklist_id}/item/{item_id}/delete', follow_redirects=True)
    assert response.status_code == 200
    
    # Verify item and all progress records are deleted
    with app.app_context():
        deleted_item = db.session.get(ChecklistItem, item_id)
        assert deleted_item is None
        
        deleted_progress1 = db.session.get(UserProgress, progress1_id)
        assert deleted_progress1 is None
        
        deleted_progress2 = db.session.get(UserProgress, progress2_id)
        assert deleted_progress2 is None
