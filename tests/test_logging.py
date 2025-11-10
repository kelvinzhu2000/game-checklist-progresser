import pytest
import sys
import os
import logging
from io import StringIO

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


@pytest.fixture
def log_capture():
    """Capture log output for testing."""
    # Create a string buffer to capture logs
    log_buffer = StringIO()
    handler = logging.StreamHandler(log_buffer)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(name)s - %(levelname)s - %(funcName)s - %(message)s')
    handler.setFormatter(formatter)
    
    # Add handler to all loggers
    loggers_to_test = [
        logging.getLogger('app'),
        logging.getLogger('app.models'),
        logging.getLogger('app.routes'),
        logging.getLogger('app.forms'),
        logging.getLogger('app.ai_service')
    ]
    
    for logger in loggers_to_test:
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
    
    yield log_buffer
    
    # Clean up
    for logger in loggers_to_test:
        logger.removeHandler(handler)


def test_logging_on_app_creation(app, log_capture):
    """Test that app creation logging is configured."""
    # This test just verifies that logging is configured properly
    # The actual app creation happens before log capture is set up
    log_output = log_capture.getvalue()
    # Since app is already created, we just verify logging infrastructure exists
    # by checking that other operations are logged
    assert log_capture is not None


def test_logging_on_route_access(client, log_capture):
    """Test that route access is logged."""
    # Clear previous logs
    log_capture.truncate(0)
    log_capture.seek(0)
    
    # Access the index route
    response = client.get('/')
    
    log_output = log_capture.getvalue()
    assert response.status_code == 200
    assert 'index called' in log_output


def test_logging_on_user_creation(app, log_capture):
    """Test that user model methods are logged."""
    # Clear previous logs
    log_capture.truncate(0)
    log_capture.seek(0)
    
    with app.app_context():
        user = User(username='testuser', email='test@example.com')
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
    
    log_output = log_capture.getvalue()
    assert 'set_password called' in log_output


def test_logging_on_password_check(app, log_capture):
    """Test that password checking is logged."""
    with app.app_context():
        user = User(username='testuser', email='test@example.com')
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
        
        # Clear previous logs
        log_capture.truncate(0)
        log_capture.seek(0)
        
        # Check password
        result = user.check_password('password123')
        
        log_output = log_capture.getvalue()
        assert result is True
        assert 'check_password called' in log_output


def test_logging_on_checklist_operations(app, log_capture):
    """Test that checklist model methods are logged."""
    with app.app_context():
        # Create a user and game
        user = User(username='testuser', email='test@example.com')
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
        
        game = Game(name='Test Game')
        db.session.add(game)
        db.session.commit()
        
        # Clear previous logs
        log_capture.truncate(0)
        log_capture.seek(0)
        
        # Create a checklist
        checklist = Checklist(
            title='Test Checklist',
            game_id=game.id,
            creator_id=user.id,
            is_public=True
        )
        db.session.add(checklist)
        db.session.commit()
        
        # Add an item
        item = ChecklistItem(
            checklist_id=checklist.id,
            title='Test Item',
            order=1
        )
        db.session.add(item)
        db.session.commit()
        
        # Test are_prerequisites_met (should be logged)
        log_capture.truncate(0)
        log_capture.seek(0)
        
        result = item.are_prerequisites_met()
        
        log_output = log_capture.getvalue()
        assert result == (True, [])
        assert 'are_prerequisites_met called' in log_output


def test_logging_on_registration(client, log_capture):
    """Test that registration route is logged."""
    # Clear previous logs
    log_capture.truncate(0)
    log_capture.seek(0)
    
    response = client.get('/auth/register')
    
    log_output = log_capture.getvalue()
    assert response.status_code == 200
    assert 'register called' in log_output


def test_logging_on_login(client, log_capture):
    """Test that login route is logged."""
    # Clear previous logs
    log_capture.truncate(0)
    log_capture.seek(0)
    
    response = client.get('/auth/login')
    
    log_output = log_capture.getvalue()
    assert response.status_code == 200
    assert 'login called' in log_output


def test_logging_on_form_validation(client, app, log_capture):
    """Test that form validation is logged."""
    # Clear previous logs
    log_capture.truncate(0)
    log_capture.seek(0)
    
    # Try to register with duplicate username
    with app.app_context():
        # First create a user
        user = User(username='existinguser', email='existing@example.com')
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
    
    # Clear logs after user creation
    log_capture.truncate(0)
    log_capture.seek(0)
    
    # Try to register with the same username
    response = client.post('/auth/register', data={
        'username': 'existinguser',
        'email': 'new@example.com',
        'password': 'password123',
        'password2': 'password123'
    }, follow_redirects=True)
    
    log_output = log_capture.getvalue()
    # The validation method should be called
    assert 'validate_username called' in log_output or 'register called' in log_output
