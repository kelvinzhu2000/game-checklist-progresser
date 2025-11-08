"""Tests for autocomplete endpoints."""
import pytest
from app import create_app, db
from app.models import User, Game, Checklist, ChecklistItem


@pytest.fixture
def app():
    """Create test app."""
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
    """Create test client."""
    return app.test_client()


@pytest.fixture
def init_database(app):
    """Initialize database with test data."""
    with app.app_context():
        # Create test users
        user = User(username='testuser', email='test@example.com')
        user.set_password('password123')
        db.session.add(user)
        
        # Create test games
        game1 = Game(name='The Legend of Zelda')
        game2 = Game(name='Super Mario Bros')
        game3 = Game(name='Minecraft')
        db.session.add_all([game1, game2, game3])
        db.session.flush()
        
        # Create test checklists
        checklist1 = Checklist(
            title='Main Quest',
            game_id=game1.id,
            description='Main story quests',
            creator_id=user.id,
            is_public=True
        )
        checklist2 = Checklist(
            title='Side Quests',
            game_id=game1.id,
            description='Side quests',
            creator_id=user.id,
            is_public=True
        )
        checklist3 = Checklist(
            title='World Completion',
            game_id=game2.id,
            description='World items',
            creator_id=user.id,
            is_public=True
        )
        db.session.add_all([checklist1, checklist2, checklist3])
        db.session.flush()
        
        # Create test items with categories
        item1 = ChecklistItem(
            checklist_id=checklist1.id,
            title='Temple of Time',
            description='Complete temple',
            category='Temples',
            order=1
        )
        item2 = ChecklistItem(
            checklist_id=checklist1.id,
            title='Fire Temple',
            description='Complete fire temple',
            category='Temples',
            order=2
        )
        item3 = ChecklistItem(
            checklist_id=checklist2.id,
            title='Find all heart pieces',
            description='Collect all hearts',
            category='Collectibles',
            order=1
        )
        item4 = ChecklistItem(
            checklist_id=checklist2.id,
            title='Catch all fish',
            description='Complete fishing',
            category='Collectibles',
            order=2
        )
        item5 = ChecklistItem(
            checklist_id=checklist3.id,
            title='World 1-1',
            description='Complete first level',
            category='World 1',
            order=1
        )
        # Item without category
        item6 = ChecklistItem(
            checklist_id=checklist1.id,
            title='Random item',
            description='No category',
            order=3
        )
        db.session.add_all([item1, item2, item3, item4, item5, item6])
        db.session.commit()


def test_get_game_names_empty(client):
    """Test getting game names when no games exist."""
    response = client.get('/api/game-names')
    assert response.status_code == 200
    data = response.get_json()
    assert 'game_names' in data
    assert data['game_names'] == []


def test_get_game_names(client, init_database):
    """Test getting all game names."""
    response = client.get('/api/game-names')
    assert response.status_code == 200
    data = response.get_json()
    assert 'game_names' in data
    assert len(data['game_names']) == 3
    # Games should be sorted alphabetically
    assert data['game_names'] == ['Minecraft', 'Super Mario Bros', 'The Legend of Zelda']


def test_get_categories_for_game(client, init_database, app):
    """Test getting categories for a specific game."""
    with app.app_context():
        # Get the Zelda game (game1)
        game = Game.query.filter_by(name='The Legend of Zelda').first()
        
        response = client.get(f'/api/categories/{game.id}')
        assert response.status_code == 200
        data = response.get_json()
        assert 'categories' in data
        # Should have two unique categories: 'Temples' and 'Collectibles'
        assert len(data['categories']) == 2
        assert 'Temples' in data['categories']
        assert 'Collectibles' in data['categories']


def test_get_categories_for_game_no_items(client, init_database, app):
    """Test getting categories for a game with checklists but no items with categories."""
    with app.app_context():
        # Create a new game with no items
        user = User.query.first()
        game = Game(name='Empty Game')
        db.session.add(game)
        db.session.flush()
        
        checklist = Checklist(
            title='Empty Checklist',
            game_id=game.id,
            description='No items',
            creator_id=user.id,
            is_public=True
        )
        db.session.add(checklist)
        db.session.commit()
        
        response = client.get(f'/api/categories/{game.id}')
        assert response.status_code == 200
        data = response.get_json()
        assert 'categories' in data
        assert data['categories'] == []


def test_get_categories_for_game_no_checklists(client, init_database, app):
    """Test getting categories for a game with no checklists."""
    with app.app_context():
        # Create a new game with no checklists
        game = Game(name='Game with no checklists')
        db.session.add(game)
        db.session.commit()
        
        response = client.get(f'/api/categories/{game.id}')
        assert response.status_code == 200
        data = response.get_json()
        assert 'categories' in data
        assert data['categories'] == []


def test_get_categories_only_from_specific_game(client, init_database, app):
    """Test that categories are only returned for the specific game."""
    with app.app_context():
        # Get the Mario game (game2)
        game = Game.query.filter_by(name='Super Mario Bros').first()
        
        response = client.get(f'/api/categories/{game.id}')
        assert response.status_code == 200
        data = response.get_json()
        assert 'categories' in data
        # Should only have 'World 1', not 'Temples' or 'Collectibles' from Zelda
        assert len(data['categories']) == 1
        assert 'World 1' in data['categories']
        assert 'Temples' not in data['categories']
        assert 'Collectibles' not in data['categories']


def test_categories_ignore_empty_and_null(client, init_database, app):
    """Test that empty and null categories are excluded."""
    with app.app_context():
        # Add items with empty and null categories
        game = Game.query.filter_by(name='Minecraft').first()
        user = User.query.first()
        
        checklist = Checklist(
            title='Test Checklist',
            game_id=game.id,
            description='Test',
            creator_id=user.id,
            is_public=True
        )
        db.session.add(checklist)
        db.session.flush()
        
        # Item with empty category
        item1 = ChecklistItem(
            checklist_id=checklist.id,
            title='Item 1',
            category='',
            order=1
        )
        # Item with null category
        item2 = ChecklistItem(
            checklist_id=checklist.id,
            title='Item 2',
            category=None,
            order=2
        )
        # Item with valid category
        item3 = ChecklistItem(
            checklist_id=checklist.id,
            title='Item 3',
            category='Building',
            order=3
        )
        db.session.add_all([item1, item2, item3])
        db.session.commit()
        
        response = client.get(f'/api/categories/{game.id}')
        assert response.status_code == 200
        data = response.get_json()
        assert 'categories' in data
        # Should only have 'Building', not empty or null
        assert len(data['categories']) == 1
        assert 'Building' in data['categories']
