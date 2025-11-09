import pytest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models import User, Game, Checklist, ChecklistItem, UserChecklist, UserProgress
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

def test_checklist_item_has_location_field(app):
    """Test that ChecklistItem model has location field."""
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
        
        # Create an item with a location
        item = ChecklistItem(
            checklist_id=checklist.id,
            title='Test Item',
            description='Test Description',
            location='City Center',
            category='Collectibles',
            order=1
        )
        db.session.add(item)
        db.session.commit()
        
        # Verify the item was created with the location
        retrieved_item = ChecklistItem.query.filter_by(checklist_id=checklist.id).first()
        assert retrieved_item is not None
        assert retrieved_item.location == 'City Center'
        assert retrieved_item.category == 'Collectibles'

def test_add_item_with_location(auth_client, app):
    """Test adding an item with a location through the form."""
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
    
    # Add an item with a location
    response = auth_client.post(f'/checklist/{checklist_id}/add_item', data={
        'title': 'New Item',
        'description': 'Item Description',
        'location': 'Downtown',
        'category': 'Achievements'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    
    with app.app_context():
        item = ChecklistItem.query.filter_by(title='New Item').first()
        assert item is not None
        assert item.location == 'Downtown'
        assert item.category == 'Achievements'

def test_batch_update_with_locations(auth_client, app):
    """Test batch updating items with locations."""
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
        
        # Create items
        item1 = ChecklistItem(
            checklist_id=checklist.id,
            title='Item 1',
            location='Location A',
            category='Category A',
            order=1
        )
        item2 = ChecklistItem(
            checklist_id=checklist.id,
            title='Item 2',
            location='Location B',
            category='Category B',
            order=2
        )
        db.session.add(item1)
        db.session.add(item2)
        db.session.commit()
        
        checklist_id = checklist.id
        item1_id = item1.id
        item2_id = item2.id
    
    # Update items via batch update
    update_data = {
        'title': 'Updated Checklist',
        'description': 'Updated description',
        'is_public': True,
        'items': [
            {
                'id': item1_id,
                'title': 'Updated Item 1',
                'description': 'Desc 1',
                'location': 'Updated Location A',
                'category': 'Updated Category A'
            },
            {
                'id': item2_id,
                'title': 'Updated Item 2',
                'description': 'Desc 2',
                'location': 'Updated Location B',
                'category': 'Updated Category B'
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
        item1 = db.session.get(ChecklistItem, item1_id)
        item2 = db.session.get(ChecklistItem, item2_id)
        assert item1.location == 'Updated Location A'
        assert item1.category == 'Updated Category A'
        assert item2.location == 'Updated Location B'
        assert item2.category == 'Updated Category B'

def test_add_new_item_with_location_via_batch_update(auth_client, app):
    """Test adding a new item with location via batch update."""
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
    
    # Add a new item via batch update
    update_data = {
        'title': 'Test Checklist',
        'description': '',
        'is_public': True,
        'items': [
            {
                'id': 'new',
                'title': 'New Item',
                'description': 'New Description',
                'location': 'New Location',
                'category': 'New Category'
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
        assert item.location == 'New Location'
        assert item.category == 'New Category'

def test_get_locations_endpoint(auth_client, app):
    """Test the API endpoint that returns unique locations for a checklist."""
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
        
        # Create items with various locations
        items_data = [
            ('Item 1', 'Location A'),
            ('Item 2', 'Location B'),
            ('Item 3', 'Location A'),
            ('Item 4', 'Location C'),
            ('Item 5', None),  # No location
            ('Item 6', ''),    # Empty location
        ]
        
        for title, location in items_data:
            item = ChecklistItem(
                checklist_id=checklist.id,
                title=title,
                location=location,
                order=1
            )
            db.session.add(item)
        
        db.session.commit()
        checklist_id = checklist.id
    
    # Get locations
    response = auth_client.get(f'/checklist/{checklist_id}/locations')
    assert response.status_code == 200
    
    data = json.loads(response.data)
    locations = data['locations']
    
    # Should only return non-empty unique locations
    assert len(locations) == 3
    assert 'Location A' in locations
    assert 'Location B' in locations
    assert 'Location C' in locations

def test_view_checklist_with_locations(auth_client, app):
    """Test viewing a checklist that has items with locations."""
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
        
        # Create items with locations
        item1 = ChecklistItem(
            checklist_id=checklist.id,
            title='Item 1',
            location='City Center',
            order=1
        )
        item2 = ChecklistItem(
            checklist_id=checklist.id,
            title='Item 2',
            location='Suburbs',
            order=2
        )
        db.session.add(item1)
        db.session.add(item2)
        db.session.commit()
        checklist_id = checklist.id
    
    # View the checklist
    response = auth_client.get(f'/checklist/{checklist_id}')
    assert response.status_code == 200
    
    # Check that location badges are shown
    assert b'City Center' in response.data
    assert b'Suburbs' in response.data
    assert b'data-location' in response.data

def test_item_without_location(auth_client, app):
    """Test that items without locations still work correctly."""
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
        
        # Create an item without a location
        item = ChecklistItem(
            checklist_id=checklist.id,
            title='Item without location',
            order=1
        )
        db.session.add(item)
        db.session.commit()
        checklist_id = checklist.id
    
    # View the checklist
    response = auth_client.get(f'/checklist/{checklist_id}')
    assert response.status_code == 200
    assert b'Item without location' in response.data

def test_get_locations_for_game_endpoint(auth_client, app):
    """Test the API endpoint that returns unique locations for a game."""
    with app.app_context():
        # Create a game
        game = Game(name='Test Game')
        db.session.add(game)
        db.session.commit()
        game_id = game.id
        
        # Get the user
        user = User.query.filter_by(username='testuser').first()
        
        # Create multiple checklists for this game
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
        db.session.add(checklist1)
        db.session.add(checklist2)
        db.session.commit()
        
        # Add items with different locations across checklists
        item1 = ChecklistItem(
            checklist_id=checklist1.id,
            title='Item 1',
            location='Downtown',
            order=1
        )
        item2 = ChecklistItem(
            checklist_id=checklist1.id,
            title='Item 2',
            location='Park',
            order=2
        )
        item3 = ChecklistItem(
            checklist_id=checklist2.id,
            title='Item 3',
            location='Downtown',  # Duplicate location
            order=1
        )
        item4 = ChecklistItem(
            checklist_id=checklist2.id,
            title='Item 4',
            location='Beach',
            order=2
        )
        db.session.add_all([item1, item2, item3, item4])
        db.session.commit()
    
    # Get locations for the game
    response = auth_client.get(f'/api/locations/{game_id}')
    assert response.status_code == 200
    
    data = json.loads(response.data)
    locations = data['locations']
    
    # Should return unique locations across all checklists
    assert len(locations) == 3
    assert 'Downtown' in locations
    assert 'Park' in locations
    assert 'Beach' in locations
