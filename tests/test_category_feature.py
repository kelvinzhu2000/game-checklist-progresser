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

def test_checklist_item_has_category_field(app):
    """Test that ChecklistItem model has category field."""
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
        
        # Create an item with a category
        item = ChecklistItem(
            checklist_id=checklist.id,
            title='Test Item',
            description='Test Description',
            category='Collectibles',
            order=1
        )
        db.session.add(item)
        db.session.commit()
        
        # Verify the item was created with the category
        retrieved_item = ChecklistItem.query.filter_by(checklist_id=checklist.id).first()
        assert retrieved_item is not None
        assert retrieved_item.category == 'Collectibles'

def test_add_item_with_category(auth_client, app):
    """Test adding an item with a category through the form."""
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
    
    # Add an item with a category
    response = auth_client.post(f'/checklist/{checklist_id}/add_item', data={
        'title': 'New Item',
        'description': 'Item Description',
        'category': 'Achievements'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    
    with app.app_context():
        item = ChecklistItem.query.filter_by(title='New Item').first()
        assert item is not None
        assert item.category == 'Achievements'

def test_batch_update_with_categories(auth_client, app):
    """Test batch updating items with categories."""
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
            category='Category A',
            order=1
        )
        item2 = ChecklistItem(
            checklist_id=checklist.id,
            title='Item 2',
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
                'category': 'Updated Category A'
            },
            {
                'id': item2_id,
                'title': 'Updated Item 2',
                'description': 'Desc 2',
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
        item1 = ChecklistItem.query.get(item1_id)
        item2 = ChecklistItem.query.get(item2_id)
        assert item1.category == 'Updated Category A'
        assert item2.category == 'Updated Category B'

def test_add_new_item_with_category_via_batch_update(auth_client, app):
    """Test adding a new item with category via batch update."""
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
        assert item.category == 'New Category'

def test_get_categories_endpoint(auth_client, app):
    """Test the API endpoint that returns unique categories for a checklist."""
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
        
        # Create items with various categories
        items_data = [
            ('Item 1', 'Category A'),
            ('Item 2', 'Category B'),
            ('Item 3', 'Category A'),
            ('Item 4', 'Category C'),
            ('Item 5', None),  # No category
            ('Item 6', ''),    # Empty category
        ]
        
        for title, category in items_data:
            item = ChecklistItem(
                checklist_id=checklist.id,
                title=title,
                category=category,
                order=1
            )
            db.session.add(item)
        
        db.session.commit()
        checklist_id = checklist.id
    
    # Get categories
    response = auth_client.get(f'/checklist/{checklist_id}/categories')
    assert response.status_code == 200
    
    data = json.loads(response.data)
    categories = data['categories']
    
    # Should only return non-empty unique categories
    assert len(categories) == 3
    assert 'Category A' in categories
    assert 'Category B' in categories
    assert 'Category C' in categories

def test_view_checklist_with_categories(auth_client, app):
    """Test viewing a checklist that has items with categories."""
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
        
        # Create items with categories
        item1 = ChecklistItem(
            checklist_id=checklist.id,
            title='Item 1',
            category='Collectibles',
            order=1
        )
        item2 = ChecklistItem(
            checklist_id=checklist.id,
            title='Item 2',
            category='Achievements',
            order=2
        )
        db.session.add(item1)
        db.session.add(item2)
        db.session.commit()
        checklist_id = checklist.id
    
    # View the checklist
    response = auth_client.get(f'/checklist/{checklist_id}')
    assert response.status_code == 200
    
    # Check that category badges are shown
    assert b'Collectibles' in response.data
    assert b'Achievements' in response.data
    assert b'data-category' in response.data

def test_item_without_category(auth_client, app):
    """Test that items without categories still work correctly."""
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
        
        # Create an item without a category
        item = ChecklistItem(
            checklist_id=checklist.id,
            title='Item without category',
            order=1
        )
        db.session.add(item)
        db.session.commit()
        checklist_id = checklist.id
    
    # View the checklist
    response = auth_client.get(f'/checklist/{checklist_id}')
    assert response.status_code == 200
    assert b'Item without category' in response.data
