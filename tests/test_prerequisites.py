import pytest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models import User, Game, Checklist, ChecklistItem, UserChecklist, UserProgress, Reward, ItemPrerequisite

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

def test_prerequisite_model_creation(app):
    """Test that ItemPrerequisite model can be created."""
    with app.app_context():
        # Create test data
        user = User(username='testuser', email='test@example.com')
        user.set_password('password')
        db.session.add(user)
        
        game = Game(name='Test Game')
        db.session.add(game)
        
        checklist = Checklist(
            title='Test Checklist',
            game_id=1,
            creator_id=1,
            is_public=True
        )
        db.session.add(checklist)
        
        item1 = ChecklistItem(
            checklist_id=1,
            title='Item 1',
            order=1
        )
        item2 = ChecklistItem(
            checklist_id=1,
            title='Item 2',
            order=2
        )
        db.session.add(item1)
        db.session.add(item2)
        db.session.commit()
        
        # Create item prerequisite
        prereq = ItemPrerequisite(
            item_id=item2.id,
            prerequisite_item_id=item1.id
        )
        db.session.add(prereq)
        db.session.commit()
        
        # Verify prerequisite was created
        assert ItemPrerequisite.query.count() == 1
        assert item2.prerequisites[0].prerequisite_item_id == item1.id

def test_prerequisite_types(app):
    """Test all three types of prerequisites."""
    with app.app_context():
        user = User(username='testuser', email='test@example.com')
        user.set_password('password')
        db.session.add(user)
        
        game = Game(name='Test Game')
        db.session.add(game)
        
        checklist = Checklist(title='Test', game_id=1, creator_id=1)
        db.session.add(checklist)
        
        item1 = ChecklistItem(checklist_id=1, title='Item 1', order=1)
        item2 = ChecklistItem(checklist_id=1, title='Item 2', order=2)
        db.session.add(item1)
        db.session.add(item2)
        
        reward = Reward(name='Gold Coin')
        db.session.add(reward)
        db.session.commit()
        
        # Type 1: Item prerequisite
        prereq1 = ItemPrerequisite(
            item_id=item2.id,
            prerequisite_item_id=item1.id
        )
        db.session.add(prereq1)
        
        # Type 2: Reward prerequisite
        prereq2 = ItemPrerequisite(
            item_id=item2.id,
            prerequisite_reward_id=reward.id,
            consumes_reward=True
        )
        db.session.add(prereq2)
        
        # Type 3: Freeform prerequisite
        prereq3 = ItemPrerequisite(
            item_id=item2.id,
            freeform_text='Complete tutorial'
        )
        db.session.add(prereq3)
        db.session.commit()
        
        # Verify all prerequisites
        assert len(item2.prerequisites) == 3
        assert item2.prerequisites[0].prerequisite_item_id == item1.id
        assert item2.prerequisites[1].prerequisite_reward_id == reward.id
        assert item2.prerequisites[1].consumes_reward == True
        assert item2.prerequisites[2].freeform_text == 'Complete tutorial'

def test_are_prerequisites_met(app):
    """Test the are_prerequisites_met() method."""
    with app.app_context():
        user = User(username='testuser', email='test@example.com')
        user.set_password('password')
        db.session.add(user)
        
        game = Game(name='Test Game')
        db.session.add(game)
        
        checklist = Checklist(title='Test', game_id=1, creator_id=1)
        db.session.add(checklist)
        
        item1 = ChecklistItem(checklist_id=1, title='Item 1', order=1)
        item2 = ChecklistItem(checklist_id=1, title='Item 2', order=2)
        db.session.add(item1)
        db.session.add(item2)
        db.session.commit()
        
        # Add prerequisite: item2 requires item1
        prereq = ItemPrerequisite(
            item_id=item2.id,
            prerequisite_item_id=item1.id
        )
        db.session.add(prereq)
        
        # Create user checklist
        user_checklist = UserChecklist(user_id=user.id, checklist_id=checklist.id)
        db.session.add(user_checklist)
        db.session.commit()
        
        # Create progress records
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
        
        # Test: item1 not completed, so item2 prerequisites not met
        are_met, unmet = item2.are_prerequisites_met(user_checklist.id)
        assert are_met == False
        assert len(unmet) == 1
        
        # Complete item1
        progress1.completed = True
        db.session.commit()
        
        # Test: item1 completed, so item2 prerequisites are met
        are_met, unmet = item2.are_prerequisites_met(user_checklist.id)
        assert are_met == True
        assert len(unmet) == 0

def test_batch_update_with_prerequisites(auth_client, app):
    """Test batch update endpoint with prerequisites."""
    client, user_id = auth_client
    
    with app.app_context():
        # Create test data
        game = Game(name='Test Game')
        db.session.add(game)
        
        checklist = Checklist(
            title='Test Checklist',
            game_id=1,
            creator_id=user_id,
            is_public=True
        )
        db.session.add(checklist)
        
        item1 = ChecklistItem(checklist_id=1, title='First Item', order=1)
        item2 = ChecklistItem(checklist_id=1, title='Second Item', order=2)
        db.session.add(item1)
        db.session.add(item2)
        db.session.commit()
        
        item1_id = item1.id
        item2_id = item2.id
    
    # Update with prerequisites
    response = client.post('/checklist/1/batch-update', 
        json={
            'title': 'Updated Checklist',
            'description': 'Test description',
            'is_public': True,
            'items': [
                {
                    'id': item1_id,
                    'title': 'First Item',
                    'description': '',
                    'location': '',
                    'category': '',
                    'rewards': [],
                    'prerequisites': []
                },
                {
                    'id': item2_id,
                    'title': 'Second Item',
                    'description': '',
                    'location': '',
                    'category': '',
                    'rewards': [],
                    'prerequisites': [
                        {
                            'type': 'item',
                            'prerequisite_item_id': item1_id
                        },
                        {
                            'type': 'freeform',
                            'freeform_text': 'Complete tutorial'
                        }
                    ]
                }
            ],
            'deleted_items': []
        },
        content_type='application/json'
    )
    
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] == True
    
    # Verify prerequisites were saved
    with app.app_context():
        item2 = ChecklistItem.query.get(item2_id)
        assert len(item2.prerequisites) == 2
        
        # Check item prerequisite
        item_prereq = [p for p in item2.prerequisites if p.prerequisite_item_id][0]
        assert item_prereq.prerequisite_item_id == item1_id
        
        # Check freeform prerequisite
        freeform_prereq = [p for p in item2.prerequisites if p.freeform_text][0]
        assert freeform_prereq.freeform_text == 'Complete tutorial'

def test_toggle_progress_with_prerequisites(auth_client, app):
    """Test that items with unmet prerequisites cannot be completed."""
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
        
        # Add prerequisite
        prereq = ItemPrerequisite(
            item_id=item2.id,
            prerequisite_item_id=item1.id
        )
        db.session.add(prereq)
        
        # Create user checklist
        user_checklist = UserChecklist(user_id=user_id, checklist_id=1)
        db.session.add(user_checklist)
        db.session.commit()
        
        # Create progress
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
        
        item2_id = item2.id
    
    # Try to complete item2 (should fail - prerequisites not met)
    response = client.post(
        f'/checklist/1/progress/{item2_id}/toggle',
        content_type='application/json'
    )
    
    assert response.status_code == 400
    data = response.get_json()
    assert data['success'] == False
    assert 'Prerequisites not met' in data['error']
    
    # Complete item1
    with app.app_context():
        progress1 = UserProgress.query.filter_by(item_id=1).first()
        progress1.completed = True
        db.session.commit()
    
    # Now try to complete item2 (should succeed)
    response = client.post(
        f'/checklist/1/progress/{item2_id}/toggle',
        content_type='application/json'
    )
    
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] == True
    assert data['completed'] == True

def test_reward_and_freeform_prerequisites(auth_client, app):
    """Test that reward and freeform prerequisites are informational only."""
    client, user_id = auth_client
    
    with app.app_context():
        # Create test data
        game = Game(name='Test Game')
        db.session.add(game)
        
        checklist = Checklist(title='Test', game_id=1, creator_id=user_id)
        db.session.add(checklist)
        
        item1 = ChecklistItem(checklist_id=1, title='Item 1', order=1)
        db.session.add(item1)
        
        reward = Reward(name='Gold')
        db.session.add(reward)
        db.session.commit()
        
        # Add reward prerequisite (informational only)
        prereq1 = ItemPrerequisite(
            item_id=item1.id,
            prerequisite_reward_id=reward.id,
            consumes_reward=True
        )
        # Add freeform prerequisite (informational only)
        prereq2 = ItemPrerequisite(
            item_id=item1.id,
            freeform_text='Talk to the wizard'
        )
        db.session.add(prereq1)
        db.session.add(prereq2)
        
        # Create user checklist
        user_checklist = UserChecklist(user_id=user_id, checklist_id=1)
        db.session.add(user_checklist)
        db.session.commit()
        
        # Create progress
        progress1 = UserProgress(
            user_checklist_id=user_checklist.id,
            item_id=item1.id,
            completed=False
        )
        db.session.add(progress1)
        db.session.commit()
        
        # Check that prerequisites are met (reward and freeform don't block)
        are_met, unmet = item1.are_prerequisites_met(user_checklist.id)
        assert are_met == True
        assert len(unmet) == 0
