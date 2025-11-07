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

@pytest.fixture
def runner(app):
    """Create a test CLI runner."""
    return app.test_cli_runner()

def test_app_creation(app):
    """Test that the app is created properly."""
    assert app is not None
    assert app.config['TESTING'] is True

def test_index_route(client):
    """Test the index route."""
    response = client.get('/')
    assert response.status_code == 200
    assert b'Game Checklist Progresser' in response.data

def test_register_page(client):
    """Test the registration page loads."""
    response = client.get('/auth/register')
    assert response.status_code == 200
    assert b'Register' in response.data

def test_login_page(client):
    """Test the login page loads."""
    response = client.get('/auth/login')
    assert response.status_code == 200
    assert b'Login' in response.data

def test_user_registration(client, app):
    """Test user registration."""
    response = client.post('/auth/register', data={
        'username': 'testuser',
        'email': 'test@example.com',
        'password': 'password123',
        'password2': 'password123'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    
    with app.app_context():
        user = User.query.filter_by(username='testuser').first()
        assert user is not None
        assert user.email == 'test@example.com'

def test_user_login(client, app):
    """Test user login."""
    with app.app_context():
        user = User(username='testuser', email='test@example.com')
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
    
    response = client.post('/auth/login', data={
        'username': 'testuser',
        'password': 'password123'
    }, follow_redirects=True)
    
    assert response.status_code == 200

def test_checklist_creation(client, app):
    """Test creating a checklist."""
    with app.app_context():
        user = User(username='testuser', email='test@example.com')
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
    
    client.post('/auth/login', data={
        'username': 'testuser',
        'password': 'password123'
    })
    
    response = client.post('/checklist/create', data={
        'title': 'Test Checklist',
        'game_name': 'Test Game',
        'description': 'A test checklist',
        'is_public': True
    }, follow_redirects=True)
    
    assert response.status_code == 200
    
    with app.app_context():
        checklist = Checklist.query.filter_by(title='Test Checklist').first()
        assert checklist is not None
        assert checklist.game.name == 'Test Game'
        
        # Verify game was created
        game = Game.query.filter_by(name='Test Game').first()
        assert game is not None

def test_browse_checklists(client, app):
    """Test browsing checklists by game."""
    with app.app_context():
        user = User(username='testuser', email='test@example.com')
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
        user_id = user.id
        
        # Create game
        game = Game(name='Test Game')
        db.session.add(game)
        db.session.commit()
        game_id = game.id
        
        checklist = Checklist(
            title='Public Checklist',
            game_id=game_id,
            creator_id=user_id,
            is_public=True
        )
        db.session.add(checklist)
        db.session.commit()
        
        # Test games page (old browse redirects to games)
        response = client.get('/browse', follow_redirects=True)
        assert response.status_code == 200
        assert b'Test Game' in response.data
        
        # Test game detail page (old browse/<id> redirects to games/<id>)
        response = client.get(f'/browse/{game_id}', follow_redirects=True)
        assert response.status_code == 200
        assert b'Public Checklist' in response.data

def test_password_hashing():
    """Test password hashing."""
    user = User(username='testuser', email='test@example.com')
    user.set_password('password123')
    
    assert user.password_hash is not None
    assert user.password_hash != 'password123'
    assert user.check_password('password123') is True
    assert user.check_password('wrongpassword') is False

def test_user_checklist_progress(app):
    """Test progress calculation."""
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
        
        item1 = ChecklistItem(checklist_id=checklist.id, title='Item 1', order=1)
        item2 = ChecklistItem(checklist_id=checklist.id, title='Item 2', order=2)
        db.session.add_all([item1, item2])
        db.session.flush()
        
        user_checklist = UserChecklist(user_id=user.id, checklist_id=checklist.id)
        db.session.add(user_checklist)
        db.session.flush()
        
        progress1 = UserProgress(user_checklist_id=user_checklist.id, item_id=item1.id, completed=True)
        progress2 = UserProgress(user_checklist_id=user_checklist.id, item_id=item2.id, completed=False)
        db.session.add_all([progress1, progress2])
        db.session.commit()
        
        assert user_checklist.get_progress_percentage() == 50

def test_delete_created_checklist(client, app):
    """Test deleting a checklist created by the user."""
    with app.app_context():
        user = User(username='testuser', email='test@example.com')
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
        user_id = user.id
        
        game = Game(name='Test Game')
        db.session.add(game)
        db.session.commit()
        game_id = game.id
        
        checklist = Checklist(
            title='Test Checklist',
            game_id=game_id,
            creator_id=user_id,
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
    
    # Delete the checklist
    response = client.post(f'/checklist/{checklist_id}/delete', follow_redirects=True)
    assert response.status_code == 200
    
    with app.app_context():
        # Verify checklist is deleted
        deleted_checklist = db.session.get(Checklist, checklist_id)
        assert deleted_checklist is None

def test_delete_created_checklist_unauthorized(client, app):
    """Test that only the creator can delete their checklist."""
    with app.app_context():
        user1 = User(username='creator', email='creator@example.com')
        user1.set_password('password123')
        user2 = User(username='other', email='other@example.com')
        user2.set_password('password123')
        db.session.add_all([user1, user2])
        db.session.commit()
        user1_id = user1.id
        
        game = Game(name='Test Game')
        db.session.add(game)
        db.session.commit()
        game_id = game.id
        
        checklist = Checklist(
            title='Test Checklist',
            game_id=game_id,
            creator_id=user1_id,
            is_public=True
        )
        db.session.add(checklist)
        db.session.commit()
        checklist_id = checklist.id
    
    # Login as different user
    client.post('/auth/login', data={
        'username': 'other',
        'password': 'password123'
    })
    
    # Try to delete the checklist (should fail)
    response = client.post(f'/checklist/{checklist_id}/delete')
    assert response.status_code == 403
    
    with app.app_context():
        # Verify checklist still exists
        checklist = db.session.get(Checklist, checklist_id)
        assert checklist is not None

def test_delete_copied_checklist(client, app):
    """Test deleting a copied checklist (removes user's copy)."""
    with app.app_context():
        user = User(username='testuser', email='test@example.com')
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
        user_id = user.id
        
        game = Game(name='Test Game')
        db.session.add(game)
        db.session.commit()
        game_id = game.id
        
        checklist = Checklist(
            title='Test Checklist',
            game_id=game_id,
            creator_id=user_id,
            is_public=True
        )
        db.session.add(checklist)
        db.session.commit()
        checklist_id = checklist.id
        
        # Create a copy
        user_checklist = UserChecklist(user_id=user_id, checklist_id=checklist_id)
        db.session.add(user_checklist)
        db.session.commit()
        user_checklist_id = user_checklist.id
    
    # Login
    client.post('/auth/login', data={
        'username': 'testuser',
        'password': 'password123'
    })
    
    # Delete the copy
    response = client.post(f'/checklist/{checklist_id}/delete-copy', follow_redirects=True)
    assert response.status_code == 200
    
    with app.app_context():
        # Verify user copy is deleted
        deleted_user_checklist = db.session.get(UserChecklist, user_checklist_id)
        assert deleted_user_checklist is None
        
        # But original checklist still exists
        original_checklist = db.session.get(Checklist, checklist_id)
        assert original_checklist is not None

def test_delete_copy_with_progress(client, app):
    """Test that deleting a copied checklist also deletes progress."""
    with app.app_context():
        user = User(username='testuser', email='test@example.com')
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
        user_id = user.id
        
        game = Game(name='Test Game')
        db.session.add(game)
        db.session.commit()
        game_id = game.id
        
        checklist = Checklist(
            title='Test Checklist',
            game_id=game_id,
            creator_id=user_id,
            is_public=True
        )
        db.session.add(checklist)
        db.session.commit()
        checklist_id = checklist.id
        
        item = ChecklistItem(checklist_id=checklist_id, title='Item 1', order=1)
        db.session.add(item)
        db.session.commit()
        item_id = item.id
        
        # Create a copy with progress
        user_checklist = UserChecklist(user_id=user_id, checklist_id=checklist_id)
        db.session.add(user_checklist)
        db.session.commit()
        user_checklist_id = user_checklist.id
        
        progress = UserProgress(user_checklist_id=user_checklist_id, item_id=item_id, completed=True)
        db.session.add(progress)
        db.session.commit()
        progress_id = progress.id
    
    # Login
    client.post('/auth/login', data={
        'username': 'testuser',
        'password': 'password123'
    })
    
    # Delete the copy
    response = client.post(f'/checklist/{checklist_id}/delete-copy', follow_redirects=True)
    assert response.status_code == 200
    
    with app.app_context():
        # Verify user copy is deleted
        deleted_user_checklist = db.session.get(UserChecklist, user_checklist_id)
        assert deleted_user_checklist is None
        
        # Verify progress is also deleted (cascade delete)
        deleted_progress = db.session.get(UserProgress, progress_id)
        assert deleted_progress is None
        
        # But original checklist and items still exist
        original_checklist = db.session.get(Checklist, checklist_id)
        assert original_checklist is not None
        original_item = db.session.get(ChecklistItem, item_id)
        assert original_item is not None
