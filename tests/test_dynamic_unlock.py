import pytest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models import User, Game, Checklist, ChecklistItem, UserChecklist, UserProgress, ItemPrerequisite

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
    """Create a test client with authenticated user."""
    with app.app_context():
        # Create a test user
        user = User(username='testuser', email='test@example.com')
        user.set_password('testpass')
        db.session.add(user)
        db.session.commit()
        user_id = user.id
    
    # Login
    client.post('/auth/login', data={
        'username': 'testuser',
        'password': 'testpass'
    })
    
    return client, user_id

def test_toggle_progress_returns_unlocked_items(auth_client, app):
    """Test that toggle_progress returns list of newly unlocked items."""
    client, user_id = auth_client
    
    with app.app_context():
        # Create test data with prerequisite chain: item1 -> item2 -> item3
        game = Game(name='Test Game')
        db.session.add(game)
        
        checklist = Checklist(title='Test', game_id=1, creator_id=user_id)
        db.session.add(checklist)
        
        item1 = ChecklistItem(checklist_id=1, title='Item 1', order=1)
        item2 = ChecklistItem(checklist_id=1, title='Item 2', order=2)
        item3 = ChecklistItem(checklist_id=1, title='Item 3', order=3)
        db.session.add(item1)
        db.session.add(item2)
        db.session.add(item3)
        db.session.commit()
        
        # Set up prerequisites: item2 requires item1, item3 requires item2
        prereq1 = ItemPrerequisite(
            item_id=item2.id,
            prerequisite_item_id=item1.id
        )
        prereq2 = ItemPrerequisite(
            item_id=item3.id,
            prerequisite_item_id=item2.id
        )
        db.session.add(prereq1)
        db.session.add(prereq2)
        
        # Create user checklist
        user_checklist = UserChecklist(user_id=user_id, checklist_id=1)
        db.session.add(user_checklist)
        db.session.commit()
        
        # Create progress records (all incomplete)
        for item in [item1, item2, item3]:
            progress = UserProgress(
                user_checklist_id=user_checklist.id,
                item_id=item.id,
                completed=False
            )
            db.session.add(progress)
        db.session.commit()
        
        item1_id = item1.id
        item2_id = item2.id
        item3_id = item3.id
    
    # Complete item1 - should unlock item2
    response = client.post(
        f'/checklist/1/progress/{item1_id}/toggle',
        content_type='application/json'
    )
    
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] == True
    assert data['completed'] == True
    assert 'unlocked_items' in data
    assert item2_id in data['unlocked_items']
    assert item3_id not in data['unlocked_items']  # item3 still locked (requires item2)
    
    # Complete item2 - should unlock item3
    response = client.post(
        f'/checklist/1/progress/{item2_id}/toggle',
        content_type='application/json'
    )
    
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] == True
    assert data['completed'] == True
    assert 'unlocked_items' in data
    assert item3_id in data['unlocked_items']

def test_toggle_progress_no_unlock_on_uncheck(auth_client, app):
    """Test that unchecking an item doesn't return unlocked_items."""
    client, user_id = auth_client
    
    with app.app_context():
        # Create test data
        game = Game(name='Test Game')
        db.session.add(game)
        
        checklist = Checklist(title='Test', game_id=1, creator_id=user_id)
        db.session.add(checklist)
        
        item1 = ChecklistItem(checklist_id=1, title='Item 1', order=1)
        item2 = ChecklistItem(checklist_id=1, title='Item 2', order=2)
        db.session.add(item1)
        db.session.add(item2)
        db.session.commit()
        
        # Set up prerequisite: item2 requires item1
        prereq = ItemPrerequisite(
            item_id=item2.id,
            prerequisite_item_id=item1.id
        )
        db.session.add(prereq)
        
        # Create user checklist
        user_checklist = UserChecklist(user_id=user_id, checklist_id=1)
        db.session.add(user_checklist)
        db.session.commit()
        
        # Create progress records with item1 completed
        progress1 = UserProgress(
            user_checklist_id=user_checklist.id,
            item_id=item1.id,
            completed=True
        )
        progress2 = UserProgress(
            user_checklist_id=user_checklist.id,
            item_id=item2.id,
            completed=False
        )
        db.session.add(progress1)
        db.session.add(progress2)
        db.session.commit()
        
        item1_id = item1.id
    
    # Uncheck item1 (toggle from completed to incomplete)
    response = client.post(
        f'/checklist/1/progress/{item1_id}/toggle',
        content_type='application/json'
    )
    
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] == True
    assert data['completed'] == False
    assert 'unlocked_items' in data
    assert len(data['unlocked_items']) == 0  # No items unlocked when unchecking

def test_toggle_progress_multiple_dependents(auth_client, app):
    """Test that completing one item can unlock multiple dependent items."""
    client, user_id = auth_client
    
    with app.app_context():
        # Create test data
        game = Game(name='Test Game')
        db.session.add(game)
        
        checklist = Checklist(title='Test', game_id=1, creator_id=user_id)
        db.session.add(checklist)
        
        # Create items: item1 is prerequisite for both item2 and item3
        item1 = ChecklistItem(checklist_id=1, title='Item 1', order=1)
        item2 = ChecklistItem(checklist_id=1, title='Item 2', order=2)
        item3 = ChecklistItem(checklist_id=1, title='Item 3', order=3)
        db.session.add(item1)
        db.session.add(item2)
        db.session.add(item3)
        db.session.commit()
        
        # Both item2 and item3 require item1
        prereq1 = ItemPrerequisite(
            item_id=item2.id,
            prerequisite_item_id=item1.id
        )
        prereq2 = ItemPrerequisite(
            item_id=item3.id,
            prerequisite_item_id=item1.id
        )
        db.session.add(prereq1)
        db.session.add(prereq2)
        
        # Create user checklist
        user_checklist = UserChecklist(user_id=user_id, checklist_id=1)
        db.session.add(user_checklist)
        db.session.commit()
        
        # Create progress records
        for item in [item1, item2, item3]:
            progress = UserProgress(
                user_checklist_id=user_checklist.id,
                item_id=item.id,
                completed=False
            )
            db.session.add(progress)
        db.session.commit()
        
        item1_id = item1.id
        item2_id = item2.id
        item3_id = item3.id
    
    # Complete item1 - should unlock both item2 and item3
    response = client.post(
        f'/checklist/1/progress/{item1_id}/toggle',
        content_type='application/json'
    )
    
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] == True
    assert data['completed'] == True
    assert 'unlocked_items' in data
    assert item2_id in data['unlocked_items']
    assert item3_id in data['unlocked_items']
    assert len(data['unlocked_items']) == 2

def test_toggle_progress_returns_locked_items(auth_client, app):
    """Test that unchecking an item returns list of newly locked items."""
    client, user_id = auth_client
    
    with app.app_context():
        # Create test data with prerequisite: item1 -> item2
        game = Game(name='Test Game')
        db.session.add(game)
        
        checklist = Checklist(title='Test', game_id=1, creator_id=user_id)
        db.session.add(checklist)
        
        item1 = ChecklistItem(checklist_id=1, title='Item 1', order=1)
        item2 = ChecklistItem(checklist_id=1, title='Item 2', order=2)
        db.session.add(item1)
        db.session.add(item2)
        db.session.commit()
        
        # item2 requires item1
        prereq = ItemPrerequisite(
            item_id=item2.id,
            prerequisite_item_id=item1.id
        )
        db.session.add(prereq)
        
        # Create user checklist
        user_checklist = UserChecklist(user_id=user_id, checklist_id=1)
        db.session.add(user_checklist)
        db.session.commit()
        
        # Create progress records with item1 completed
        progress1 = UserProgress(
            user_checklist_id=user_checklist.id,
            item_id=item1.id,
            completed=True
        )
        progress2 = UserProgress(
            user_checklist_id=user_checklist.id,
            item_id=item2.id,
            completed=False
        )
        db.session.add(progress1)
        db.session.add(progress2)
        db.session.commit()
        
        item1_id = item1.id
        item2_id = item2.id
    
    # Uncheck item1 - should lock item2
    response = client.post(
        f'/checklist/1/progress/{item1_id}/toggle',
        content_type='application/json'
    )
    
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] == True
    assert data['completed'] == False
    assert 'locked_items' in data
    assert item2_id in data['locked_items']
    assert len(data['locked_items']) == 1

def test_toggle_progress_locks_multiple_dependents(auth_client, app):
    """Test that unchecking one item can lock multiple dependent items."""
    client, user_id = auth_client
    
    with app.app_context():
        # Create test data
        game = Game(name='Test Game')
        db.session.add(game)
        
        checklist = Checklist(title='Test', game_id=1, creator_id=user_id)
        db.session.add(checklist)
        
        # Create items: item1 is prerequisite for both item2 and item3
        item1 = ChecklistItem(checklist_id=1, title='Item 1', order=1)
        item2 = ChecklistItem(checklist_id=1, title='Item 2', order=2)
        item3 = ChecklistItem(checklist_id=1, title='Item 3', order=3)
        db.session.add(item1)
        db.session.add(item2)
        db.session.add(item3)
        db.session.commit()
        
        # Both item2 and item3 require item1
        prereq1 = ItemPrerequisite(
            item_id=item2.id,
            prerequisite_item_id=item1.id
        )
        prereq2 = ItemPrerequisite(
            item_id=item3.id,
            prerequisite_item_id=item1.id
        )
        db.session.add(prereq1)
        db.session.add(prereq2)
        
        # Create user checklist
        user_checklist = UserChecklist(user_id=user_id, checklist_id=1)
        db.session.add(user_checklist)
        db.session.commit()
        
        # Create progress records with item1 completed
        for item in [item1, item2, item3]:
            progress = UserProgress(
                user_checklist_id=user_checklist.id,
                item_id=item.id,
                completed=True if item.id == item1.id else False
            )
            db.session.add(progress)
        db.session.commit()
        
        item1_id = item1.id
        item2_id = item2.id
        item3_id = item3.id
    
    # Uncheck item1 - should lock both item2 and item3
    response = client.post(
        f'/checklist/1/progress/{item1_id}/toggle',
        content_type='application/json'
    )
    
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] == True
    assert data['completed'] == False
    assert 'locked_items' in data
    assert item2_id in data['locked_items']
    assert item3_id in data['locked_items']
    assert len(data['locked_items']) == 2

def test_toggle_progress_chain_locking(auth_client, app):
    """Test prerequisite chain locking (unchecking A locks B, which affects items depending on B)."""
    client, user_id = auth_client
    
    with app.app_context():
        # Create test data with prerequisite chain: item1 -> item2 -> item3
        game = Game(name='Test Game')
        db.session.add(game)
        
        checklist = Checklist(title='Test', game_id=1, creator_id=user_id)
        db.session.add(checklist)
        
        item1 = ChecklistItem(checklist_id=1, title='Item 1', order=1)
        item2 = ChecklistItem(checklist_id=1, title='Item 2', order=2)
        item3 = ChecklistItem(checklist_id=1, title='Item 3', order=3)
        db.session.add(item1)
        db.session.add(item2)
        db.session.add(item3)
        db.session.commit()
        
        # Set up prerequisites: item2 requires item1, item3 requires item2
        prereq1 = ItemPrerequisite(
            item_id=item2.id,
            prerequisite_item_id=item1.id
        )
        prereq2 = ItemPrerequisite(
            item_id=item3.id,
            prerequisite_item_id=item2.id
        )
        db.session.add(prereq1)
        db.session.add(prereq2)
        
        # Create user checklist
        user_checklist = UserChecklist(user_id=user_id, checklist_id=1)
        db.session.add(user_checklist)
        db.session.commit()
        
        # Create progress records with all items completed
        for item in [item1, item2, item3]:
            progress = UserProgress(
                user_checklist_id=user_checklist.id,
                item_id=item.id,
                completed=True
            )
            db.session.add(progress)
        db.session.commit()
        
        item1_id = item1.id
        item2_id = item2.id
        item3_id = item3.id
    
    # Uncheck item1 - should lock BOTH item2 and item3 (with chaining)
    response = client.post(
        f'/checklist/1/progress/{item1_id}/toggle',
        content_type='application/json'
    )
    
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] == True
    assert data['completed'] == False
    assert 'locked_items' in data
    assert item2_id in data['locked_items']
    # With proper chaining, item3 should also be locked when item1 is unchecked
    # because item3 depends on item2, which depends on item1
    assert item3_id in data['locked_items']
