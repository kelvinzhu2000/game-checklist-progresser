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

def test_dependent_items_persist_check_state_when_prerequisite_unchecked(auth_client, app):
    """
    Test that when a prerequisite is unchecked, dependent items that were already
    checked remain checked in the database but should be treated as not completed
    for reward purposes until the prerequisite is rechecked.
    
    Current behavior (BUG): item2 gets unchecked in database when item1 is unchecked
    Desired behavior: item2 stays checked in database but is considered "locked"
    """
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
        
        # Create progress records - both unchecked initially
        progress1 = UserProgress(
            user_checklist_id=user_checklist.id,
            item_id=item1.id,
            completed=False
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
        user_checklist_id = user_checklist.id
    
    # Step 1: Complete item1 (should unlock item2)
    response = client.post(
        f'/checklist/1/progress/{item1_id}/toggle',
        content_type='application/json'
    )
    assert response.status_code == 200
    
    # Step 2: Complete item2
    response = client.post(
        f'/checklist/1/progress/{item2_id}/toggle',
        content_type='application/json'
    )
    assert response.status_code == 200
    
    # Verify both items are marked as completed
    with app.app_context():
        progress1 = UserProgress.query.filter_by(
            user_checklist_id=user_checklist_id,
            item_id=item1_id
        ).first()
        progress2 = UserProgress.query.filter_by(
            user_checklist_id=user_checklist_id,
            item_id=item2_id
        ).first()
        
        assert progress1.completed == True
        assert progress2.completed == True
        
        # Store original completed_at for item2 to verify it doesn't change
        item2_completed_at = progress2.completed_at
    
    # Step 3: Uncheck item1 (should lock item2 but NOT uncheck it in database)
    response = client.post(
        f'/checklist/1/progress/{item1_id}/toggle',
        content_type='application/json'
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data['locked_items'] == [item2_id]
    
    # Step 4: Check database state - item2 should STILL be marked as checked
    # This is the DESIRED behavior that currently FAILS
    with app.app_context():
        progress1 = UserProgress.query.filter_by(
            user_checklist_id=user_checklist_id,
            item_id=item1_id
        ).first()
        progress2 = UserProgress.query.filter_by(
            user_checklist_id=user_checklist_id,
            item_id=item2_id
        ).first()
        
        # item1 should be unchecked
        assert progress1.completed == False
        
        # CRITICAL: item2 should STILL be checked in database (user's actual state)
        # This preserves the user's work when prerequisites are temporarily not met
        # Currently this FAILS because the current code doesn't implement this
        print(f"DEBUG: progress2.completed = {progress2.completed}")
        assert progress2.completed == True, "Dependent item should remain checked in database when prerequisite is unchecked"
        assert progress2.completed_at == item2_completed_at, "completed_at should not change"
    
    # Step 5: Re-check item1 - item2 should still be checked
    response = client.post(
        f'/checklist/1/progress/{item1_id}/toggle',
        content_type='application/json'
    )
    assert response.status_code == 200
    
    # Verify item2 is still checked (didn't lose state)
    with app.app_context():
        progress2 = UserProgress.query.filter_by(
            user_checklist_id=user_checklist_id,
            item_id=item2_id
        ).first()
        
        assert progress2.completed == True
        assert progress2.completed_at == item2_completed_at

def test_locked_items_dont_count_in_rewards(auth_client, app):
    """
    Test that locked items (due to unmet prerequisites) don't count toward
    reward tallies even if they are marked as checked in the database.
    """
    # This test will be implemented after we update the reward calculation logic
    pass
