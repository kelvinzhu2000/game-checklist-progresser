import pytest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models import User, Game, Checklist, ChecklistItem, UserChecklist, UserProgress, ItemPrerequisite, Reward, ItemReward

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

def test_item_prerequisite_chaining_on_uncheck(auth_client, app):
    """
    Test that unchecking an item cascades to all transitive dependencies.
    
    Setup: A -> B -> C (where -> means "is prerequisite for")
    When all are checked and A is unchecked:
    - B should be locked (direct dependency)
    - C should be locked (transitive dependency through B)
    """
    client, user_id = auth_client
    
    with app.app_context():
        # Create test data with prerequisite chain: item1 -> item2 -> item3
        game = Game(name='Test Game')
        db.session.add(game)
        
        checklist = Checklist(title='Test', game_id=1, creator_id=user_id)
        db.session.add(checklist)
        
        item1 = ChecklistItem(checklist_id=1, title='Item A', order=1)
        item2 = ChecklistItem(checklist_id=1, title='Item B', order=2)
        item3 = ChecklistItem(checklist_id=1, title='Item C', order=3)
        db.session.add_all([item1, item2, item3])
        db.session.commit()
        
        # Set up prerequisites: item2 requires item1, item3 requires item2
        prereq1 = ItemPrerequisite(item_id=item2.id, prerequisite_item_id=item1.id)
        prereq2 = ItemPrerequisite(item_id=item3.id, prerequisite_item_id=item2.id)
        db.session.add_all([prereq1, prereq2])
        
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
    
    # Uncheck item1 - should lock BOTH item2 and item3
    response = client.post(
        f'/checklist/1/progress/{item1_id}/toggle',
        content_type='application/json'
    )
    
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] == True
    assert data['completed'] == False
    assert 'locked_items' in data
    assert item2_id in data['locked_items'], "Item B should be locked (direct dependency)"
    assert item3_id in data['locked_items'], "Item C should be locked (transitive dependency)"

def test_reward_prerequisite_chaining_on_uncheck(auth_client, app):
    """
    Test the exact scenario from the problem statement:
    - Item A: rewards 5 puzzle pieces
    - Item B: requires 3 puzzle pieces, rewards 3 puzzle pieces  
    - Item C: requires 3 puzzle pieces (from B)
    
    When all are checked and A is unchecked:
    - B should be locked (insufficient puzzle pieces)
    - C should be locked (B is locked, so it can't provide puzzle pieces)
    """
    client, user_id = auth_client
    
    with app.app_context():
        # Create test data
        game = Game(name='Test Game')
        db.session.add(game)
        
        checklist = Checklist(title='Test', game_id=1, creator_id=user_id)
        db.session.add(checklist)
        db.session.commit()
        
        # Create reward type
        puzzle_reward = Reward(name='Puzzle Pieces')
        db.session.add(puzzle_reward)
        db.session.commit()
        
        # Create items
        itemA = ChecklistItem(checklist_id=1, title='Item A (rewards 5 puzzles)', order=1)
        itemB = ChecklistItem(checklist_id=1, title='Item B (requires 3, rewards 3 puzzles)', order=2)
        itemC = ChecklistItem(checklist_id=1, title='Item C (requires 3 puzzles)', order=3)
        db.session.add_all([itemA, itemB, itemC])
        db.session.commit()
        
        # Item A rewards 5 puzzle pieces
        rewardA = ItemReward(checklist_item_id=itemA.id, reward_id=puzzle_reward.id, amount=5)
        db.session.add(rewardA)
        
        # Item B requires 3 puzzle pieces and rewards 3 puzzle pieces
        prereqB = ItemPrerequisite(
            item_id=itemB.id,
            prerequisite_reward_id=puzzle_reward.id,
            reward_amount=3
        )
        rewardB = ItemReward(checklist_item_id=itemB.id, reward_id=puzzle_reward.id, amount=3)
        db.session.add_all([prereqB, rewardB])
        
        # Item C requires 3 puzzle pieces
        prereqC = ItemPrerequisite(
            item_id=itemC.id,
            prerequisite_reward_id=puzzle_reward.id,
            reward_amount=3
        )
        db.session.add(prereqC)
        db.session.commit()
        
        # Create user checklist
        user_checklist = UserChecklist(user_id=user_id, checklist_id=1)
        db.session.add(user_checklist)
        db.session.commit()
        
        # Create progress records with all items completed
        for item in [itemA, itemB, itemC]:
            progress = UserProgress(
                user_checklist_id=user_checklist.id,
                item_id=item.id,
                completed=True
            )
            db.session.add(progress)
        db.session.commit()
        
        itemA_id = itemA.id
        itemB_id = itemB.id
        itemC_id = itemC.id
    
    # Uncheck Item A - should lock BOTH Item B and Item C
    response = client.post(
        f'/checklist/1/progress/{itemA_id}/toggle',
        content_type='application/json'
    )
    
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] == True
    assert data['completed'] == False
    assert 'locked_items' in data
    assert itemB_id in data['locked_items'], "Item B should be locked (needs 3 puzzles, only 0 available)"
    assert itemC_id in data['locked_items'], "Item C should be locked (Item B can't provide puzzles when locked)"

def test_mixed_prerequisite_chaining(auth_client, app):
    """
    Test chaining with both item and reward prerequisites.
    
    Setup:
    - Item A: rewards 5 puzzle pieces
    - Item B: requires Item A (item prereq), rewards 3 puzzle pieces
    - Item C: requires 3 puzzle pieces (reward prereq)
    
    When all are checked and A is unchecked:
    - B should be locked (Item A prerequisite not met)
    - C should be locked (B can't provide puzzles when locked)
    """
    client, user_id = auth_client
    
    with app.app_context():
        game = Game(name='Test Game')
        db.session.add(game)
        
        checklist = Checklist(title='Test', game_id=1, creator_id=user_id)
        db.session.add(checklist)
        db.session.commit()
        
        puzzle_reward = Reward(name='Puzzle Pieces')
        db.session.add(puzzle_reward)
        db.session.commit()
        
        itemA = ChecklistItem(checklist_id=1, title='Item A', order=1)
        itemB = ChecklistItem(checklist_id=1, title='Item B', order=2)
        itemC = ChecklistItem(checklist_id=1, title='Item C', order=3)
        db.session.add_all([itemA, itemB, itemC])
        db.session.commit()
        
        # Item A rewards 5 puzzle pieces
        rewardA = ItemReward(checklist_item_id=itemA.id, reward_id=puzzle_reward.id, amount=5)
        db.session.add(rewardA)
        
        # Item B requires Item A (item prerequisite) and rewards 3 puzzle pieces
        prereqB = ItemPrerequisite(item_id=itemB.id, prerequisite_item_id=itemA.id)
        rewardB = ItemReward(checklist_item_id=itemB.id, reward_id=puzzle_reward.id, amount=3)
        db.session.add_all([prereqB, rewardB])
        
        # Item C requires 3 puzzle pieces (reward prerequisite)
        prereqC = ItemPrerequisite(
            item_id=itemC.id,
            prerequisite_reward_id=puzzle_reward.id,
            reward_amount=3
        )
        db.session.add(prereqC)
        db.session.commit()
        
        user_checklist = UserChecklist(user_id=user_id, checklist_id=1)
        db.session.add(user_checklist)
        db.session.commit()
        
        for item in [itemA, itemB, itemC]:
            progress = UserProgress(
                user_checklist_id=user_checklist.id,
                item_id=item.id,
                completed=True
            )
            db.session.add(progress)
        db.session.commit()
        
        itemA_id = itemA.id
        itemB_id = itemB.id
        itemC_id = itemC.id
    
    # Uncheck Item A
    response = client.post(
        f'/checklist/1/progress/{itemA_id}/toggle',
        content_type='application/json'
    )
    
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] == True
    assert data['completed'] == False
    assert 'locked_items' in data
    assert itemB_id in data['locked_items'], "Item B should be locked (Item A prerequisite not met)"
    assert itemC_id in data['locked_items'], "Item C should be locked (needs puzzles from B which is locked)"

def test_item_prerequisite_chaining_on_check(auth_client, app):
    """
    Test that checking an item cascades unlocks to all transitive dependencies.
    
    Setup: A -> B -> C
    Starting state: All unchecked, B and C are locked
    When A is checked:
    - B should be unlocked
    - C should remain locked (still needs B to be checked)
    
    Then when B is checked:
    - C should be unlocked
    """
    client, user_id = auth_client
    
    with app.app_context():
        game = Game(name='Test Game')
        db.session.add(game)
        
        checklist = Checklist(title='Test', game_id=1, creator_id=user_id)
        db.session.add(checklist)
        
        item1 = ChecklistItem(checklist_id=1, title='Item A', order=1)
        item2 = ChecklistItem(checklist_id=1, title='Item B', order=2)
        item3 = ChecklistItem(checklist_id=1, title='Item C', order=3)
        db.session.add_all([item1, item2, item3])
        db.session.commit()
        
        prereq1 = ItemPrerequisite(item_id=item2.id, prerequisite_item_id=item1.id)
        prereq2 = ItemPrerequisite(item_id=item3.id, prerequisite_item_id=item2.id)
        db.session.add_all([prereq1, prereq2])
        
        user_checklist = UserChecklist(user_id=user_id, checklist_id=1)
        db.session.add(user_checklist)
        db.session.commit()
        
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
    
    # Check item1 - should unlock item2 only
    response = client.post(
        f'/checklist/1/progress/{item1_id}/toggle',
        content_type='application/json'
    )
    
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] == True
    assert data['completed'] == True
    assert item2_id in data['unlocked_items'], "Item B should be unlocked"
    assert item3_id not in data['unlocked_items'], "Item C should remain locked (needs B to be checked)"
    
    # Now check item2 - should unlock item3
    response = client.post(
        f'/checklist/1/progress/{item2_id}/toggle',
        content_type='application/json'
    )
    
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] == True
    assert data['completed'] == True
    assert item3_id in data['unlocked_items'], "Item C should be unlocked"

def test_deep_prerequisite_chain(auth_client, app):
    """
    Test a deeper chain: A -> B -> C -> D -> E
    Unchecking A should lock all downstream items.
    """
    client, user_id = auth_client
    
    with app.app_context():
        game = Game(name='Test Game')
        db.session.add(game)
        
        checklist = Checklist(title='Test', game_id=1, creator_id=user_id)
        db.session.add(checklist)
        db.session.commit()
        
        items = []
        for i in range(5):
            item = ChecklistItem(checklist_id=1, title=f'Item {chr(65+i)}', order=i+1)
            items.append(item)
            db.session.add(item)
        db.session.commit()
        
        # Create chain of prerequisites
        for i in range(1, 5):
            prereq = ItemPrerequisite(
                item_id=items[i].id,
                prerequisite_item_id=items[i-1].id
            )
            db.session.add(prereq)
        db.session.commit()
        
        user_checklist = UserChecklist(user_id=user_id, checklist_id=1)
        db.session.add(user_checklist)
        db.session.commit()
        
        # All items completed
        for item in items:
            progress = UserProgress(
                user_checklist_id=user_checklist.id,
                item_id=item.id,
                completed=True
            )
            db.session.add(progress)
        db.session.commit()
        
        item_ids = [item.id for item in items]
    
    # Uncheck first item - should lock all others
    response = client.post(
        f'/checklist/1/progress/{item_ids[0]}/toggle',
        content_type='application/json'
    )
    
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] == True
    assert data['completed'] == False
    
    # All downstream items should be locked
    for i in range(1, 5):
        assert item_ids[i] in data['locked_items'], f"Item {chr(65+i)} should be locked"
