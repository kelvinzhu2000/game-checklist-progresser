import pytest
import sys
import os
import json
from unittest.mock import patch, MagicMock
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


def test_edit_checklist_page_requires_login(client, app):
    """Test that edit page requires login."""
    with app.app_context():
        user = User(username='edituser', email='edituser@example.com')
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
    
    # Try to access edit page without login
    response = client.get(f'/checklist/{checklist_id}/edit')
    assert response.status_code == 302  # Redirect to login


def test_edit_checklist_only_by_creator(client, app):
    """Test that only the creator can edit a checklist."""
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
    
    # Try to access edit page
    response = client.get(f'/checklist/{checklist_id}/edit')
    assert response.status_code == 403  # Forbidden


def test_edit_checklist_basic_update(client, app):
    """Test editing checklist without AI prompt."""
    with app.app_context():
        user = User(username='edituser', email='edituser@example.com')
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
    
    # Login as creator
    client.post('/auth/login', data={
        'username': 'edituser',
        'password': 'password123'
    })
    
    # Update checklist
    response = client.post(f'/checklist/{checklist_id}/edit', data={
        'title': 'Updated Title',
        'description': 'Updated description',
        # is_public checkbox not included means False
        'ai_prompt': ''  # No AI prompt
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert b'Checklist updated successfully!' in response.data
    
    # Verify changes
    with app.app_context():
        checklist = Checklist.query.get(checklist_id)
        assert checklist.title == 'Updated Title'
        assert checklist.description == 'Updated description'
        assert checklist.is_public == False


def test_edit_checklist_with_ai_prompt(client, app):
    """Test editing checklist with AI prompt generates new items."""
    with app.app_context():
        user = User(username='aiuser', email='aiuser@example.com')
        user.set_password('password123')
        db.session.add(user)
        
        game = Game(name='Test Game')
        db.session.add(game)
        db.session.flush()
        
        checklist = Checklist(
            title='Original Checklist',
            game_id=game.id,
            creator_id=user.id,
            is_public=True
        )
        db.session.add(checklist)
        db.session.flush()
        
        # Add an existing item
        item1 = ChecklistItem(
            checklist_id=checklist.id,
            title='Existing Item',
            description='Original item',
            order=1
        )
        db.session.add(item1)
        db.session.commit()
        checklist_id = checklist.id
    
    # Login
    client.post('/auth/login', data={
        'username': 'aiuser',
        'password': 'password123'
    })
    
    # Mock AI response
    mock_items = [
        {"title": "AI Generated Item 1", "description": "First AI item"},
        {"title": "AI Generated Item 2", "description": "Second AI item"}
    ]
    
    with patch('app.routes.generate_checklist_items') as mock_generate:
        mock_generate.return_value = mock_items
        
        response = client.post(f'/checklist/{checklist_id}/edit', data={
            'title': 'Updated Title',
            'description': 'Updated description',
            'ai_prompt': 'Add more items for collectibles',
            'is_public': True
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'AI-generated items' in response.data
        
        # Verify checklist was updated and items were added
        with app.app_context():
            checklist = Checklist.query.get(checklist_id)
            assert checklist.title == 'Updated Title'
            
            items = ChecklistItem.query.filter_by(checklist_id=checklist_id).order_by(ChecklistItem.order).all()
            assert len(items) == 3  # 1 original + 2 new AI items
            assert items[0].title == 'Existing Item'
            assert items[1].title == 'AI Generated Item 1'
            assert items[2].title == 'AI Generated Item 2'
            assert items[1].order == 2
            assert items[2].order == 3


def test_edit_checklist_with_failed_ai_generation(client, app):
    """Test editing checklist when AI generation fails."""
    with app.app_context():
        user = User(username='aiuser2', email='aiuser2@example.com')
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
        'username': 'aiuser2',
        'password': 'password123'
    })
    
    # Mock AI failure
    with patch('app.routes.generate_checklist_items') as mock_generate:
        mock_generate.return_value = None
        
        response = client.post(f'/checklist/{checklist_id}/edit', data={
            'title': 'Updated Title',
            'description': 'Updated description',
            'ai_prompt': 'Generate items',
            'is_public': True
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'AI generation failed' in response.data
        
        # Verify checklist was updated even though AI failed
        with app.app_context():
            checklist = Checklist.query.get(checklist_id)
            assert checklist.title == 'Updated Title'


def test_edit_checklist_page_loads_existing_data(client, app):
    """Test that edit page pre-populates with existing data."""
    with app.app_context():
        user = User(username='edituser', email='edituser@example.com')
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
        'username': 'edituser',
        'password': 'password123'
    })
    
    # Get edit page
    response = client.get(f'/checklist/{checklist_id}/edit')
    
    assert response.status_code == 200
    assert b'Original Title' in response.data
    assert b'Original description' in response.data
    assert b'Edit Checklist' in response.data
