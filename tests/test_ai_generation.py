import pytest
import sys
import os
from unittest.mock import patch, MagicMock
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models import User, Checklist, ChecklistItem
from app.ai_service import generate_checklist_items


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


def test_ai_service_without_api_key():
    """Test AI service when API key is not available."""
    with patch.dict(os.environ, {}, clear=True):
        result = generate_checklist_items(
            game_name="Test Game",
            title="Test Checklist",
            prompt="Generate items for testing"
        )
        assert result is None


def test_ai_service_with_valid_response():
    """Test AI service with a mocked valid OpenAI response."""
    mock_items = [
        {"title": "Item 1", "description": "Description 1"},
        {"title": "Item 2", "description": "Description 2"}
    ]
    
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = str(mock_items).replace("'", '"')
    
    with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
        with patch('app.ai_service.OpenAI') as mock_openai:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client
            
            result = generate_checklist_items(
                game_name="Test Game",
                title="Test Checklist",
                prompt="Generate test items"
            )
            
            assert result is not None
            assert len(result) == 2
            assert result[0]['title'] == 'Item 1'
            assert result[1]['title'] == 'Item 2'


def test_ai_service_with_markdown_wrapped_json():
    """Test AI service handles markdown-wrapped JSON responses."""
    mock_items = [{"title": "Item 1", "description": "Desc 1"}]
    json_str = str(mock_items).replace("'", '"')
    
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = f"```json\n{json_str}\n```"
    
    with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
        with patch('app.ai_service.OpenAI') as mock_openai:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client
            
            result = generate_checklist_items(
                game_name="Test Game",
                title="Test Checklist",
                prompt="Generate test items"
            )
            
            assert result is not None
            assert len(result) == 1


def test_ai_service_handles_exception():
    """Test AI service handles exceptions gracefully."""
    with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
        with patch('app.ai_service.OpenAI') as mock_openai:
            mock_openai.side_effect = Exception("API Error")
            
            result = generate_checklist_items(
                game_name="Test Game",
                title="Test Checklist",
                prompt="Generate test items"
            )
            
            assert result is None


def test_create_checklist_with_ai_prompt(client, app):
    """Test creating a checklist with AI generation."""
    with app.app_context():
        user = User(username='aiuser1', email='aiuser1@example.com')
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
    
    # Login
    client.post('/auth/login', data={
        'username': 'aiuser1',
        'password': 'password123'
    })
    
    # Mock AI response
    mock_items = [
        {"title": "Complete Tutorial", "description": "Finish the game tutorial"},
        {"title": "Defeat Boss", "description": "Beat the first boss"}
    ]
    
    with patch('app.routes.generate_checklist_items') as mock_generate:
        mock_generate.return_value = mock_items
        
        response = client.post('/checklist/create', data={
            'title': 'AI Generated Checklist',
            'game_name': 'Test Game',
            'description': 'A test checklist',
            'ai_prompt': 'Create a beginner checklist',
            'is_public': True
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'AI-generated items' in response.data
        
        # Verify checklist was created with items
        with app.app_context():
            checklist = Checklist.query.filter_by(title='AI Generated Checklist').first()
            assert checklist is not None
            items = ChecklistItem.query.filter_by(checklist_id=checklist.id).all()
            assert len(items) == 2
            assert items[0].title == 'Complete Tutorial'
            assert items[1].title == 'Defeat Boss'


def test_create_checklist_with_failed_ai_generation(client, app):
    """Test creating a checklist when AI generation fails."""
    with app.app_context():
        user = User(username='aiuser2', email='aiuser2@example.com')
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
    
    # Login
    client.post('/auth/login', data={
        'username': 'aiuser2',
        'password': 'password123'
    })
    
    # Mock AI failure
    with patch('app.routes.generate_checklist_items') as mock_generate:
        mock_generate.return_value = None
        
        response = client.post('/checklist/create', data={
            'title': 'Failed AI Checklist',
            'game_name': 'Test Game',
            'description': 'A test checklist',
            'ai_prompt': 'Generate items',
            'is_public': True
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'AI generation failed' in response.data
        
        # Verify checklist was created but without items
        with app.app_context():
            checklist = Checklist.query.filter_by(title='Failed AI Checklist').first()
            assert checklist is not None
            items = ChecklistItem.query.filter_by(checklist_id=checklist.id).all()
            assert len(items) == 0


def test_create_checklist_without_ai_prompt(client, app):
    """Test creating a checklist without AI prompt still works."""
    with app.app_context():
        user = User(username='aiuser3', email='aiuser3@example.com')
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
    
    # Login
    client.post('/auth/login', data={
        'username': 'aiuser3',
        'password': 'password123'
    })
    
    response = client.post('/checklist/create', data={
        'title': 'Manual Checklist',
        'game_name': 'Test Game',
        'description': 'A manual checklist',
        'ai_prompt': '',  # Empty prompt
        'is_public': True
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert b'You can now add items' in response.data
    
    # Verify checklist was created without items
    with app.app_context():
        checklist = Checklist.query.filter_by(title='Manual Checklist').first()
        assert checklist is not None
        items = ChecklistItem.query.filter_by(checklist_id=checklist.id).all()
        assert len(items) == 0
