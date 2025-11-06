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

def test_my_games_page(authenticated_user, app):
    """Test that my games page loads."""
    response = authenticated_user.get('/my-games')
    assert response.status_code == 200
    assert b'My Games' in response.data

def test_my_games_shows_user_games(authenticated_user, app):
    """Test that my games page shows games from user's checklists."""
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
    
    response = authenticated_user.get('/my-games')
    assert response.status_code == 200
    assert b'The Legend of Zelda' in response.data
    assert b'Super Mario Bros' in response.data

def test_select_game(authenticated_user, app):
    """Test selecting a game."""
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
    
    response = authenticated_user.get(f'/select-game/{game_id}', follow_redirects=True)
    assert response.status_code == 200
    assert b'Test Game' in response.data

def test_my_checklists_redirects_without_game(authenticated_user, app):
    """Test that my checklists redirects to my games when no game is selected."""
    response = authenticated_user.get('/my-checklists')
    assert response.status_code == 302
    assert '/my-games' in response.location

def test_my_checklists_with_selected_game(authenticated_user, app):
    """Test that my checklists shows only checklists for selected game."""
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
    
    # Select Zelda game
    authenticated_user.get(f'/select-game/{game1_id}')
    
    # Check my checklists page
    response = authenticated_user.get('/my-checklists')
    assert response.status_code == 200
    assert b'Zelda Quest' in response.data
    assert b'Mario Quest' not in response.data

def test_clear_game_selection(authenticated_user, app):
    """Test clearing the game selection."""
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
    
    # Select a game
    authenticated_user.get(f'/select-game/{game_id}')
    
    # Clear selection
    response = authenticated_user.get('/clear-game', follow_redirects=True)
    assert response.status_code == 200
    assert b'Game selection cleared' in response.data

def test_create_checklist_with_selected_game(authenticated_user, app):
    """Test that create checklist pre-fills the game name when a game is selected."""
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
    
    # Select a game
    authenticated_user.get(f'/select-game/{game_id}')
    
    # Visit create page
    response = authenticated_user.get('/checklist/create')
    assert response.status_code == 200
    assert b'Selected Game' in response.data

def test_copy_checklist_sets_game_context(authenticated_user, app):
    """Test that copying a checklist sets the game context."""
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
    
    # Copy the checklist
    response = authenticated_user.post(f'/checklist/{checklist_id}/copy', follow_redirects=True)
    assert response.status_code == 200
    assert b'Adventure Game' in response.data

def test_game_stats_in_my_games(authenticated_user, app):
    """Test that my games page shows correct statistics."""
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
    
    response = authenticated_user.get('/my-games')
    assert response.status_code == 200
    assert b'Created: 2' in response.data
