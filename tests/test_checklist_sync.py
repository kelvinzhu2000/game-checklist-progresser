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

def test_new_items_synced_to_user_copies(client, app):
    """Test that new items added to a checklist are synced to all user copies."""
    with app.app_context():
        # Create users
        creator = User(username='creator', email='creator@example.com')
        creator.set_password('password123')
        user1 = User(username='user1', email='user1@example.com')
        user1.set_password('password123')
        user2 = User(username='user2', email='user2@example.com')
        user2.set_password('password123')
        db.session.add_all([creator, user1, user2])
        db.session.commit()
        creator_id = creator.id
        user1_id = user1.id
        user2_id = user2.id
        
        # Create a game and checklist
        game = Game(name='Test Game')
        db.session.add(game)
        db.session.commit()
        game_id = game.id
        
        checklist = Checklist(
            title='Test Checklist',
            game_id=game_id,
            creator_id=creator_id,
            is_public=True
        )
        db.session.add(checklist)
        db.session.commit()
        checklist_id = checklist.id
        
        # Add initial items
        item1 = ChecklistItem(checklist_id=checklist_id, title='Item 1', order=1)
        item2 = ChecklistItem(checklist_id=checklist_id, title='Item 2', order=2)
        db.session.add_all([item1, item2])
        db.session.commit()
        item1_id = item1.id
        item2_id = item2.id
        
        # User1 and User2 copy the checklist
        user_checklist1 = UserChecklist(user_id=user1_id, checklist_id=checklist_id)
        user_checklist2 = UserChecklist(user_id=user2_id, checklist_id=checklist_id)
        db.session.add_all([user_checklist1, user_checklist2])
        db.session.commit()
        
        # Create initial progress entries
        for user_checklist in [user_checklist1, user_checklist2]:
            for item in [item1, item2]:
                progress = UserProgress(
                    user_checklist_id=user_checklist.id,
                    item_id=item.id,
                    completed=False
                )
                db.session.add(progress)
        db.session.commit()
        
        # Verify initial state - 2 items, 2 progress entries per user
        assert UserProgress.query.filter_by(user_checklist_id=user_checklist1.id).count() == 2
        assert UserProgress.query.filter_by(user_checklist_id=user_checklist2.id).count() == 2
    
    # Login as creator
    client.post('/auth/login', data={
        'username': 'creator',
        'password': 'password123'
    })
    
    # Creator adds a new item via batch update
    with app.app_context():
        checklist = db.session.get(Checklist, checklist_id)
        item1 = db.session.get(ChecklistItem, item1_id)
        item2 = db.session.get(ChecklistItem, item2_id)
        
        response = client.post(f'/checklist/{checklist_id}/batch-update',
            json={
                'title': checklist.title,
                'description': checklist.description,
                'is_public': checklist.is_public,
                'items': [
                    {
                        'id': item1_id,
                        'title': item1.title,
                        'description': item1.description or '',
                        'location': item1.location or '',
                        'category': item1.category or '',
                        'rewards': [],
                        'prerequisites': []
                    },
                    {
                        'id': item2_id,
                        'title': item2.title,
                        'description': item2.description or '',
                        'location': item2.location or '',
                        'category': item2.category or '',
                        'rewards': [],
                        'prerequisites': []
                    },
                    {
                        'id': 'new',
                        'title': 'Item 3',
                        'description': 'New item added by creator',
                        'location': '',
                        'category': '',
                        'rewards': [],
                        'prerequisites': []
                    }
                ],
                'deleted_items': []
            }
        )
        
        assert response.status_code == 200
        assert response.json['success'] is True
    
    # Verify that the new item was created and synced to all user copies
    with app.app_context():
        user_checklist1 = UserChecklist.query.filter_by(user_id=user1_id, checklist_id=checklist_id).first()
        user_checklist2 = UserChecklist.query.filter_by(user_id=user2_id, checklist_id=checklist_id).first()
        
        # Should now have 3 progress entries per user (including the new item)
        progress_count1 = UserProgress.query.filter_by(user_checklist_id=user_checklist1.id).count()
        progress_count2 = UserProgress.query.filter_by(user_checklist_id=user_checklist2.id).count()
        
        assert progress_count1 == 3, f"Expected 3 progress entries for user1, got {progress_count1}"
        assert progress_count2 == 3, f"Expected 3 progress entries for user2, got {progress_count2}"
        
        # Verify the new progress entries exist and are not completed
        new_item = ChecklistItem.query.filter_by(checklist_id=checklist_id, title='Item 3').first()
        assert new_item is not None
        
        progress1_new = UserProgress.query.filter_by(
            user_checklist_id=user_checklist1.id,
            item_id=new_item.id
        ).first()
        progress2_new = UserProgress.query.filter_by(
            user_checklist_id=user_checklist2.id,
            item_id=new_item.id
        ).first()
        
        assert progress1_new is not None, "User1 should have progress entry for new item"
        assert progress2_new is not None, "User2 should have progress entry for new item"
        assert progress1_new.completed is False
        assert progress2_new.completed is False

def test_new_item_via_add_item_synced_to_user_copies(client, app):
    """Test that new items added via add_item route are synced to all user copies."""
    with app.app_context():
        # Create users
        creator = User(username='creator', email='creator@example.com')
        creator.set_password('password123')
        user1 = User(username='user1', email='user1@example.com')
        user1.set_password('password123')
        db.session.add_all([creator, user1])
        db.session.commit()
        creator_id = creator.id
        user1_id = user1.id
        
        # Create a game and checklist
        game = Game(name='Test Game')
        db.session.add(game)
        db.session.commit()
        
        checklist = Checklist(
            title='Test Checklist',
            game_id=game.id,
            creator_id=creator_id,
            is_public=True
        )
        db.session.add(checklist)
        db.session.commit()
        checklist_id = checklist.id
        
        # Add initial item
        item1 = ChecklistItem(checklist_id=checklist_id, title='Item 1', order=1)
        db.session.add(item1)
        db.session.commit()
        
        # User1 copies the checklist
        user_checklist = UserChecklist(user_id=user1_id, checklist_id=checklist_id)
        db.session.add(user_checklist)
        db.session.commit()
        
        # Create initial progress entry
        progress = UserProgress(
            user_checklist_id=user_checklist.id,
            item_id=item1.id,
            completed=False
        )
        db.session.add(progress)
        db.session.commit()
        
        # Verify initial state
        assert UserProgress.query.filter_by(user_checklist_id=user_checklist.id).count() == 1
    
    # Login as creator
    client.post('/auth/login', data={
        'username': 'creator',
        'password': 'password123'
    })
    
    # Creator adds a new item via add_item route
    response = client.post(f'/checklist/{checklist_id}/add_item',
        data={
            'title': 'Item 2',
            'description': 'New item added by creator',
            'location': '',
            'category': ''
        },
        follow_redirects=True
    )
    
    assert response.status_code == 200
    
    # Verify that the new item was synced to user's copy
    with app.app_context():
        user_checklist = UserChecklist.query.filter_by(user_id=user1_id, checklist_id=checklist_id).first()
        
        # Should now have 2 progress entries
        progress_count = UserProgress.query.filter_by(user_checklist_id=user_checklist.id).count()
        assert progress_count == 2, f"Expected 2 progress entries, got {progress_count}"
        
        # Verify the new progress entry exists
        new_item = ChecklistItem.query.filter_by(checklist_id=checklist_id, title='Item 2').first()
        assert new_item is not None
        
        progress_new = UserProgress.query.filter_by(
            user_checklist_id=user_checklist.id,
            item_id=new_item.id
        ).first()
        
        assert progress_new is not None, "User should have progress entry for new item"
        assert progress_new.completed is False

def test_deleted_items_removed_from_user_copies(client, app):
    """Test that deleted items are removed from user progress (cascade delete)."""
    with app.app_context():
        # Create users
        creator = User(username='creator', email='creator@example.com')
        creator.set_password('password123')
        user1 = User(username='user1', email='user1@example.com')
        user1.set_password('password123')
        db.session.add_all([creator, user1])
        db.session.commit()
        creator_id = creator.id
        user1_id = user1.id
        
        # Create a game and checklist
        game = Game(name='Test Game')
        db.session.add(game)
        db.session.commit()
        
        checklist = Checklist(
            title='Test Checklist',
            game_id=game.id,
            creator_id=creator_id,
            is_public=True
        )
        db.session.add(checklist)
        db.session.commit()
        checklist_id = checklist.id
        
        # Add items
        item1 = ChecklistItem(checklist_id=checklist_id, title='Item 1', order=1)
        item2 = ChecklistItem(checklist_id=checklist_id, title='Item 2', order=2)
        db.session.add_all([item1, item2])
        db.session.commit()
        item1_id = item1.id
        item2_id = item2.id
        
        # User1 copies the checklist
        user_checklist = UserChecklist(user_id=user1_id, checklist_id=checklist_id)
        db.session.add(user_checklist)
        db.session.commit()
        
        # Create progress entries
        progress1 = UserProgress(user_checklist_id=user_checklist.id, item_id=item1_id, completed=True)
        progress2 = UserProgress(user_checklist_id=user_checklist.id, item_id=item2_id, completed=False)
        db.session.add_all([progress1, progress2])
        db.session.commit()
        progress2_id = progress2.id
        
        # Verify initial state
        assert UserProgress.query.filter_by(user_checklist_id=user_checklist.id).count() == 2
    
    # Login as creator
    client.post('/auth/login', data={
        'username': 'creator',
        'password': 'password123'
    })
    
    # Creator deletes item2 via batch update
    with app.app_context():
        checklist = db.session.get(Checklist, checklist_id)
        item1 = db.session.get(ChecklistItem, item1_id)
        
        response = client.post(f'/checklist/{checklist_id}/batch-update',
            json={
                'title': checklist.title,
                'description': checklist.description,
                'is_public': checklist.is_public,
                'items': [
                    {
                        'id': item1_id,
                        'title': item1.title,
                        'description': item1.description or '',
                        'location': item1.location or '',
                        'category': item1.category or '',
                        'rewards': [],
                        'prerequisites': []
                    }
                ],
                'deleted_items': [item2_id]
            }
        )
        
        assert response.status_code == 200
    
    # Verify that the progress entry for deleted item is also deleted
    with app.app_context():
        user_checklist = UserChecklist.query.filter_by(user_id=user1_id, checklist_id=checklist_id).first()
        
        # Should now have only 1 progress entry
        progress_count = UserProgress.query.filter_by(user_checklist_id=user_checklist.id).count()
        assert progress_count == 1, f"Expected 1 progress entry after deletion, got {progress_count}"
        
        # Verify the deleted progress entry is gone
        deleted_progress = db.session.get(UserProgress, progress2_id)
        assert deleted_progress is None, "Progress entry for deleted item should be removed"
        
        # Verify the remaining progress is for item1
        remaining_progress = UserProgress.query.filter_by(user_checklist_id=user_checklist.id).first()
        assert remaining_progress.item_id == item1_id

def test_user_can_toggle_progress_on_synced_items(client, app):
    """Test that users can interact with items that were added after they copied the checklist."""
    with app.app_context():
        # Create users
        creator = User(username='creator', email='creator@example.com')
        creator.set_password('password123')
        user1 = User(username='user1', email='user1@example.com')
        user1.set_password('password123')
        db.session.add_all([creator, user1])
        db.session.commit()
        creator_id = creator.id
        user1_id = user1.id
        
        # Create a game and checklist
        game = Game(name='Test Game')
        db.session.add(game)
        db.session.commit()
        
        checklist = Checklist(
            title='Test Checklist',
            game_id=game.id,
            creator_id=creator_id,
            is_public=True
        )
        db.session.add(checklist)
        db.session.commit()
        checklist_id = checklist.id
        
        # Add initial item
        item1 = ChecklistItem(checklist_id=checklist_id, title='Item 1', order=1)
        db.session.add(item1)
        db.session.commit()
        item1_id = item1.id
        
        # User1 copies the checklist
        user_checklist = UserChecklist(user_id=user1_id, checklist_id=checklist_id)
        db.session.add(user_checklist)
        db.session.commit()
        
        # Create initial progress entry
        progress1 = UserProgress(user_checklist_id=user_checklist.id, item_id=item1_id, completed=False)
        db.session.add(progress1)
        db.session.commit()
    
    # Login as creator and add a new item
    client.post('/auth/login', data={
        'username': 'creator',
        'password': 'password123'
    })
    
    client.post(f'/checklist/{checklist_id}/add_item',
        data={
            'title': 'Item 2',
            'description': 'Added after user copied',
            'location': '',
            'category': ''
        },
        follow_redirects=True
    )
    
    # Logout and login as user1
    client.get('/auth/logout')
    client.post('/auth/login', data={
        'username': 'user1',
        'password': 'password123'
    })
    
    # User1 should be able to toggle progress on the new item
    with app.app_context():
        new_item = ChecklistItem.query.filter_by(checklist_id=checklist_id, title='Item 2').first()
        assert new_item is not None
        new_item_id = new_item.id
    
    # Try to toggle progress on the new item
    response = client.post(
        f'/checklist/{checklist_id}/progress/{new_item_id}/toggle',
        headers={'X-Requested-With': 'XMLHttpRequest'},
        content_type='application/json'
    )
    
    # Should succeed without errors
    assert response.status_code == 200
    assert response.json['success'] is True
    assert response.json['completed'] is True
    
    # Verify progress was updated
    with app.app_context():
        user_checklist = UserChecklist.query.filter_by(user_id=user1_id, checklist_id=checklist_id).first()
        progress = UserProgress.query.filter_by(
            user_checklist_id=user_checklist.id,
            item_id=new_item_id
        ).first()
        
        assert progress is not None
        assert progress.completed is True
