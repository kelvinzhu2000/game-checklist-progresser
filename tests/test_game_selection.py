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
def authenticated_user(client, app):
    """Create and login a test user."""
    with app.app_context():
        user = User(username='testuser', email='test@example.com')
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
    
    client.post('/auth/login', data={
        'username': 'testuser',
        'password': 'password123'
    })
    return client

def test_games_page(authenticated_user, app):
    """Test that games page loads."""
    response = authenticated_user.get('/games')
    assert response.status_code == 200
    assert b'Games' in response.data

def test_games_shows_all_games(authenticated_user, app):
    """Test that games page shows all games."""
    with app.app_context():
        user = User.query.filter_by(username='testuser').first()
        
        # Create games
        game1 = Game(name='The Legend of Zelda')
        game2 = Game(name='Super Mario Bros')
        db.session.add_all([game1, game2])
        db.session.commit()
        
        # Create checklists for different games
        checklist1 = Checklist(
            title='Zelda Checklist',
            game_id=game1.id,
            creator_id=user.id,
            is_public=True
        )
        checklist2 = Checklist(
            title='Mario Checklist',
            game_id=game2.id,
            creator_id=user.id,
            is_public=True
        )
        db.session.add_all([checklist1, checklist2])
        db.session.commit()
    
    response = authenticated_user.get('/games')
    assert response.status_code == 200
    assert b'The Legend of Zelda' in response.data
    assert b'Super Mario Bros' in response.data

def test_game_detail(authenticated_user, app):
    """Test viewing game detail page."""
    with app.app_context():
        user = User.query.filter_by(username='testuser').first()
        
        game = Game(name='Test Game')
        db.session.add(game)
        db.session.commit()
        game_id = game.id
        
        checklist = Checklist(
            title='Test Checklist',
            game_id=game_id,
            creator_id=user.id,
            is_public=True
        )
        db.session.add(checklist)
        db.session.commit()
    
    response = authenticated_user.get(f'/games/{game_id}')
    assert response.status_code == 200
    assert b'Test Game' in response.data

def test_legacy_my_games_redirects(authenticated_user, app):
    """Test that legacy my-games route redirects to games page."""
    response = authenticated_user.get('/my-games')
    assert response.status_code == 302
    assert '/games' in response.location

def test_legacy_my_checklists_redirects(authenticated_user, app):
    """Test that legacy my-checklists route redirects to games page."""
    response = authenticated_user.get('/my-checklists')
    assert response.status_code == 302
    assert '/games' in response.location

def test_game_detail_with_user_checklists(authenticated_user, app):
    """Test that game detail page shows checklists for specific game."""
    with app.app_context():
        user = User.query.filter_by(username='testuser').first()
        
        # Create games
        game1 = Game(name='The Legend of Zelda')
        game2 = Game(name='Super Mario Bros')
        db.session.add_all([game1, game2])
        db.session.commit()
        
        # Create checklists for different games
        checklist1 = Checklist(
            title='Zelda Quest',
            game_id=game1.id,
            creator_id=user.id,
            is_public=True
        )
        checklist2 = Checklist(
            title='Mario Quest',
            game_id=game2.id,
            creator_id=user.id,
            is_public=True
        )
        db.session.add_all([checklist1, checklist2])
        db.session.commit()
        game1_id = game1.id
    
    # Check game detail page shows only Zelda checklists
    response = authenticated_user.get(f'/games/{game1_id}')
    assert response.status_code == 200
    assert b'Zelda Quest' in response.data
    assert b'Mario Quest' not in response.data

def test_legacy_clear_game_redirects(authenticated_user, app):
    """Test that legacy clear-game route redirects to games page."""
    response = authenticated_user.get('/clear-game')
    assert response.status_code == 302
    assert '/games' in response.location

def test_create_checklist_with_game_id(authenticated_user, app):
    """Test that create checklist pre-fills the game name when game_id is provided."""
    with app.app_context():
        user = User.query.filter_by(username='testuser').first()
        
        game = Game(name='Selected Game')
        db.session.add(game)
        db.session.commit()
        game_id = game.id
        
        checklist = Checklist(
            title='Existing Checklist',
            game_id=game_id,
            creator_id=user.id,
            is_public=True
        )
        db.session.add(checklist)
        db.session.commit()
    
    # Visit create page with game_id
    
    # Visit create page with game_id
    response = authenticated_user.get(f'/checklist/create/{game_id}')
    assert response.status_code == 200
    assert b'Selected Game' in response.data

def test_copy_checklist_redirects_to_game_detail(authenticated_user, app):
    """Test that copying a checklist redirects to game detail page."""
    with app.app_context():
        # Create a different user who created the checklist
        creator = User(username='creator', email='creator@example.com')
        creator.set_password('password123')
        db.session.add(creator)
        db.session.flush()
        
        game = Game(name='Adventure Game')
        db.session.add(game)
        db.session.flush()
        
        checklist = Checklist(
            title='Public Checklist',
            game_id=game.id,
            creator_id=creator.id,
            is_public=True
        )
        db.session.add(checklist)
        db.session.commit()
        checklist_id = checklist.id
        game_id = game.id
    
    # Copy the checklist
    response = authenticated_user.post(f'/checklist/{checklist_id}/copy', follow_redirects=True)
    assert response.status_code == 200
    assert b'Adventure Game' in response.data

def test_game_stats_in_games_page(authenticated_user, app):
    """Test that games page shows correct statistics."""
    with app.app_context():
        user = User.query.filter_by(username='testuser').first()
        
        game = Game(name='Test Game')
        db.session.add(game)
        db.session.commit()
        game_id = game.id
        
        # Create 2 checklists for the same game
        checklist1 = Checklist(
            title='Checklist 1',
            game_id=game_id,
            creator_id=user.id,
            is_public=True
        )
        checklist2 = Checklist(
            title='Checklist 2',
            game_id=game_id,
            creator_id=user.id,
            is_public=True
        )
        db.session.add_all([checklist1, checklist2])
        db.session.commit()
    
    response = authenticated_user.get('/games')
    assert response.status_code == 200
    assert b'Created by you: 2' in response.data
