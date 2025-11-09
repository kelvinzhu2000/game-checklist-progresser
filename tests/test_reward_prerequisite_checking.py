"""Tests for reward prerequisite checking and locking feature."""

import pytest
from app import create_app, db
from app.models import (User, Game, Checklist, ChecklistItem, UserChecklist, 
                        UserProgress, Reward, ItemReward, ItemPrerequisite)
from config import TestingConfig


@pytest.fixture
def app():
    """Create application for testing."""
    app = create_app()
    app.config.from_object(TestingConfig)
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def authenticated_user(client, app):
    """Create and authenticate a test user."""
    with app.app_context():
        user = User(username='testuser', email='test@example.com')
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
        user_id = user.id
    
    # Log in
    client.post('/auth/login', data={
        'username': 'testuser',
        'password': 'password123'
    }, follow_redirects=True)
    
    return user_id


def test_get_reward_tally_basic(app, authenticated_user):
    """Test basic reward tally calculation."""
    with app.app_context():
        # Create game and checklist
        game = Game(name='Test Game Basic Tally')
        db.session.add(game)
        db.session.commit()
        
        checklist = Checklist(
            title='Test Checklist',
            game_id=game.id,
            creator_id=authenticated_user,
            is_public=True
        )
        db.session.add(checklist)
        db.session.commit()
        
        # Create reward
        reward = Reward(name='Gold Coin')
        db.session.add(reward)
        db.session.flush()
        
        # Create items with rewards
        item1 = ChecklistItem(checklist_id=checklist.id, title='Item 1', order=1)
        item2 = ChecklistItem(checklist_id=checklist.id, title='Item 2', order=2)
        db.session.add(item1)
        db.session.add(item2)
        db.session.flush()
        
        # Add rewards to items
        db.session.add(ItemReward(checklist_item_id=item1.id, reward_id=reward.id, amount=5))
        db.session.add(ItemReward(checklist_item_id=item2.id, reward_id=reward.id, amount=3))
        db.session.commit()
        
        # Create user checklist
        user_checklist = UserChecklist(user_id=authenticated_user, checklist_id=checklist.id)
        db.session.add(user_checklist)
        db.session.commit()
        
        # Create progress - only item1 is completed
        progress1 = UserProgress(user_checklist_id=user_checklist.id, item_id=item1.id, completed=True)
        progress2 = UserProgress(user_checklist_id=user_checklist.id, item_id=item2.id, completed=False)
        db.session.add(progress1)
        db.session.add(progress2)
        db.session.commit()
        
        # Test tally - should only count completed item1
        tally = user_checklist.get_reward_tally(reward_id=reward.id)
        assert tally == 5, f"Expected 5 gold coins, got {tally}"


def test_get_reward_tally_with_location_filter(app, authenticated_user):
    """Test reward tally calculation with location filter."""
    with app.app_context():
        # Create game and checklist
        game = Game(name='Test Game')
        db.session.add(game)
        db.session.commit()
        
        checklist = Checklist(
            title='Test Checklist',
            game_id=game.id,
            creator_id=authenticated_user,
            is_public=True
        )
        db.session.add(checklist)
        db.session.commit()
        
        # Create reward
        reward = Reward(name='Puzzle Piece')
        db.session.add(reward)
        db.session.flush()
        
        # Create items with different locations
        item1 = ChecklistItem(checklist_id=checklist.id, title='Item 1', location='London', order=1)
        item2 = ChecklistItem(checklist_id=checklist.id, title='Item 2', location='Boston', order=2)
        item3 = ChecklistItem(checklist_id=checklist.id, title='Item 3', location='London', order=3)
        db.session.add(item1)
        db.session.add(item2)
        db.session.add(item3)
        db.session.flush()
        
        # Add rewards to all items
        db.session.add(ItemReward(checklist_item_id=item1.id, reward_id=reward.id, amount=2))
        db.session.add(ItemReward(checklist_item_id=item2.id, reward_id=reward.id, amount=2))
        db.session.add(ItemReward(checklist_item_id=item3.id, reward_id=reward.id, amount=3))
        db.session.commit()
        
        # Create user checklist
        user_checklist = UserChecklist(user_id=authenticated_user, checklist_id=checklist.id)
        db.session.add(user_checklist)
        db.session.commit()
        
        # Complete all items
        for item in [item1, item2, item3]:
            progress = UserProgress(user_checklist_id=user_checklist.id, item_id=item.id, completed=True)
            db.session.add(progress)
        db.session.commit()
        
        # Test tally without filter - should count all
        tally_all = user_checklist.get_reward_tally(reward_id=reward.id)
        assert tally_all == 7, f"Expected 7 total puzzle pieces, got {tally_all}"
        
        # Test tally with London filter - should only count items from London
        tally_london = user_checklist.get_reward_tally(reward_id=reward.id, location='London')
        assert tally_london == 5, f"Expected 5 puzzle pieces from London, got {tally_london}"
        
        # Test tally with Boston filter
        tally_boston = user_checklist.get_reward_tally(reward_id=reward.id, location='Boston')
        assert tally_boston == 2, f"Expected 2 puzzle pieces from Boston, got {tally_boston}"


def test_get_reward_tally_with_category_filter(app, authenticated_user):
    """Test reward tally calculation with category filter."""
    with app.app_context():
        # Create game and checklist
        game = Game(name='Test Game')
        db.session.add(game)
        db.session.commit()
        
        checklist = Checklist(
            title='Test Checklist',
            game_id=game.id,
            creator_id=authenticated_user,
            is_public=True
        )
        db.session.add(checklist)
        db.session.commit()
        
        # Create reward
        reward = Reward(name='Star')
        db.session.add(reward)
        db.session.flush()
        
        # Create items with different categories
        item1 = ChecklistItem(checklist_id=checklist.id, title='Item 1', category='Main Quest', order=1)
        item2 = ChecklistItem(checklist_id=checklist.id, title='Item 2', category='Side Quest', order=2)
        item3 = ChecklistItem(checklist_id=checklist.id, title='Item 3', category='Main Quest', order=3)
        db.session.add(item1)
        db.session.add(item2)
        db.session.add(item3)
        db.session.flush()
        
        # Add rewards to all items
        db.session.add(ItemReward(checklist_item_id=item1.id, reward_id=reward.id, amount=1))
        db.session.add(ItemReward(checklist_item_id=item2.id, reward_id=reward.id, amount=1))
        db.session.add(ItemReward(checklist_item_id=item3.id, reward_id=reward.id, amount=1))
        db.session.commit()
        
        # Create user checklist
        user_checklist = UserChecklist(user_id=authenticated_user, checklist_id=checklist.id)
        db.session.add(user_checklist)
        db.session.commit()
        
        # Complete all items
        for item in [item1, item2, item3]:
            progress = UserProgress(user_checklist_id=user_checklist.id, item_id=item.id, completed=True)
            db.session.add(progress)
        db.session.commit()
        
        # Test tally with Main Quest filter
        tally_main = user_checklist.get_reward_tally(reward_id=reward.id, category='Main Quest')
        assert tally_main == 2, f"Expected 2 stars from Main Quest, got {tally_main}"
        
        # Test tally with Side Quest filter
        tally_side = user_checklist.get_reward_tally(reward_id=reward.id, category='Side Quest')
        assert tally_side == 1, f"Expected 1 star from Side Quest, got {tally_side}"


def test_reward_prerequisite_locks_item(app, authenticated_user):
    """Test that items are locked when reward prerequisites are not met."""
    with app.app_context():
        # Create game and checklist
        game = Game(name='Test Game')
        db.session.add(game)
        db.session.commit()
        
        checklist = Checklist(
            title='Test Checklist',
            game_id=game.id,
            creator_id=authenticated_user,
            is_public=True
        )
        db.session.add(checklist)
        db.session.commit()
        
        # Create reward
        reward = Reward(name='Key')
        db.session.add(reward)
        db.session.flush()
        
        # Create items
        item1 = ChecklistItem(checklist_id=checklist.id, title='Find Key 1', order=1)
        item2 = ChecklistItem(checklist_id=checklist.id, title='Find Key 2', order=2)
        item3 = ChecklistItem(checklist_id=checklist.id, title='Open Door', order=3)
        db.session.add(item1)
        db.session.add(item2)
        db.session.add(item3)
        db.session.flush()
        
        # Items 1 and 2 give keys
        db.session.add(ItemReward(checklist_item_id=item1.id, reward_id=reward.id, amount=1))
        db.session.add(ItemReward(checklist_item_id=item2.id, reward_id=reward.id, amount=1))
        
        # Item 3 requires 2 keys
        prereq = ItemPrerequisite(
            item_id=item3.id,
            prerequisite_reward_id=reward.id,
            reward_amount=2
        )
        db.session.add(prereq)
        db.session.commit()
        
        # Create user checklist
        user_checklist = UserChecklist(user_id=authenticated_user, checklist_id=checklist.id)
        db.session.add(user_checklist)
        db.session.commit()
        
        # Create progress - only item1 completed
        for item in [item1, item2, item3]:
            progress = UserProgress(
                user_checklist_id=user_checklist.id, 
                item_id=item.id, 
                completed=(item.id == item1.id)
            )
            db.session.add(progress)
        db.session.commit()
        
        # Check if item3 prerequisites are met (should not be - only 1 key collected)
        are_met, unmet = item3.are_prerequisites_met(user_checklist.id)
        assert not are_met, "Item should be locked - only 1 of 2 keys collected"
        assert len(unmet) == 1, "Should have 1 unmet prerequisite"


def test_reward_prerequisite_unlocks_item(app, authenticated_user):
    """Test that items are unlocked when reward prerequisites are met."""
    with app.app_context():
        # Create game and checklist
        game = Game(name='Test Game')
        db.session.add(game)
        db.session.commit()
        
        checklist = Checklist(
            title='Test Checklist',
            game_id=game.id,
            creator_id=authenticated_user,
            is_public=True
        )
        db.session.add(checklist)
        db.session.commit()
        
        # Create reward
        reward = Reward(name='Key')
        db.session.add(reward)
        db.session.flush()
        
        # Create items
        item1 = ChecklistItem(checklist_id=checklist.id, title='Find Key 1', order=1)
        item2 = ChecklistItem(checklist_id=checklist.id, title='Find Key 2', order=2)
        item3 = ChecklistItem(checklist_id=checklist.id, title='Open Door', order=3)
        db.session.add(item1)
        db.session.add(item2)
        db.session.add(item3)
        db.session.flush()
        
        # Items 1 and 2 give keys
        db.session.add(ItemReward(checklist_item_id=item1.id, reward_id=reward.id, amount=1))
        db.session.add(ItemReward(checklist_item_id=item2.id, reward_id=reward.id, amount=1))
        
        # Item 3 requires 2 keys
        prereq = ItemPrerequisite(
            item_id=item3.id,
            prerequisite_reward_id=reward.id,
            reward_amount=2
        )
        db.session.add(prereq)
        db.session.commit()
        
        # Create user checklist
        user_checklist = UserChecklist(user_id=authenticated_user, checklist_id=checklist.id)
        db.session.add(user_checklist)
        db.session.commit()
        
        # Create progress - both item1 and item2 completed
        for item in [item1, item2, item3]:
            progress = UserProgress(
                user_checklist_id=user_checklist.id, 
                item_id=item.id, 
                completed=(item.id in [item1.id, item2.id])
            )
            db.session.add(progress)
        db.session.commit()
        
        # Check if item3 prerequisites are met (should be - 2 keys collected)
        are_met, unmet = item3.are_prerequisites_met(user_checklist.id)
        assert are_met, "Item should be unlocked - 2 of 2 keys collected"
        assert len(unmet) == 0, "Should have no unmet prerequisites"


def test_reward_prerequisite_with_location_filter_locks(app, authenticated_user):
    """Test that location-filtered reward prerequisites work correctly."""
    with app.app_context():
        # Create game and checklist
        game = Game(name='Test Game')
        db.session.add(game)
        db.session.commit()
        
        checklist = Checklist(
            title='Test Checklist',
            game_id=game.id,
            creator_id=authenticated_user,
            is_public=True
        )
        db.session.add(checklist)
        db.session.commit()
        
        # Create reward
        reward = Reward(name='Puzzle Piece')
        db.session.add(reward)
        db.session.flush()
        
        # Create items - puzzle pieces from different locations
        item1 = ChecklistItem(checklist_id=checklist.id, title='Puzzle from London 1', location='London', order=1)
        item2 = ChecklistItem(checklist_id=checklist.id, title='Puzzle from London 2', location='London', order=2)
        item3 = ChecklistItem(checklist_id=checklist.id, title='Puzzle from Boston', location='Boston', order=3)
        item4 = ChecklistItem(checklist_id=checklist.id, title='Complete London Puzzle', order=4)
        db.session.add(item1)
        db.session.add(item2)
        db.session.add(item3)
        db.session.add(item4)
        db.session.flush()
        
        # Add puzzle pieces as rewards
        db.session.add(ItemReward(checklist_item_id=item1.id, reward_id=reward.id, amount=3))
        db.session.add(ItemReward(checklist_item_id=item2.id, reward_id=reward.id, amount=2))
        db.session.add(ItemReward(checklist_item_id=item3.id, reward_id=reward.id, amount=2))
        
        # Item 4 requires 5 puzzle pieces from London
        prereq = ItemPrerequisite(
            item_id=item4.id,
            prerequisite_reward_id=reward.id,
            reward_amount=5,
            reward_location='London'
        )
        db.session.add(prereq)
        db.session.commit()
        
        # Create user checklist
        user_checklist = UserChecklist(user_id=authenticated_user, checklist_id=checklist.id)
        db.session.add(user_checklist)
        db.session.commit()
        
        # Complete items 1 and 3 (3 from London, 2 from Boston)
        for item in [item1, item2, item3, item4]:
            progress = UserProgress(
                user_checklist_id=user_checklist.id,
                item_id=item.id,
                completed=(item.id in [item1.id, item3.id])
            )
            db.session.add(progress)
        db.session.commit()
        
        # Check if item4 prerequisites are met
        # Should NOT be met - only 3 of 5 puzzle pieces from London
        are_met, unmet = item4.are_prerequisites_met(user_checklist.id)
        assert not are_met, "Item should be locked - only 3 of 5 puzzle pieces from London"
        assert len(unmet) == 1, "Should have 1 unmet prerequisite"


def test_reward_prerequisite_with_location_filter_unlocks(app, authenticated_user):
    """Test that location-filtered reward prerequisites unlock correctly."""
    with app.app_context():
        # Create game and checklist
        game = Game(name='Test Game')
        db.session.add(game)
        db.session.commit()
        
        checklist = Checklist(
            title='Test Checklist',
            game_id=game.id,
            creator_id=authenticated_user,
            is_public=True
        )
        db.session.add(checklist)
        db.session.commit()
        
        # Create reward
        reward = Reward(name='Puzzle Piece')
        db.session.add(reward)
        db.session.flush()
        
        # Create items - puzzle pieces from different locations
        item1 = ChecklistItem(checklist_id=checklist.id, title='Puzzle from London 1', location='London', order=1)
        item2 = ChecklistItem(checklist_id=checklist.id, title='Puzzle from London 2', location='London', order=2)
        item3 = ChecklistItem(checklist_id=checklist.id, title='Puzzle from Boston', location='Boston', order=3)
        item4 = ChecklistItem(checklist_id=checklist.id, title='Complete London Puzzle', order=4)
        db.session.add(item1)
        db.session.add(item2)
        db.session.add(item3)
        db.session.add(item4)
        db.session.flush()
        
        # Add puzzle pieces as rewards
        db.session.add(ItemReward(checklist_item_id=item1.id, reward_id=reward.id, amount=3))
        db.session.add(ItemReward(checklist_item_id=item2.id, reward_id=reward.id, amount=2))
        db.session.add(ItemReward(checklist_item_id=item3.id, reward_id=reward.id, amount=2))
        
        # Item 4 requires 5 puzzle pieces from London
        prereq = ItemPrerequisite(
            item_id=item4.id,
            prerequisite_reward_id=reward.id,
            reward_amount=5,
            reward_location='London'
        )
        db.session.add(prereq)
        db.session.commit()
        
        # Create user checklist
        user_checklist = UserChecklist(user_id=authenticated_user, checklist_id=checklist.id)
        db.session.add(user_checklist)
        db.session.commit()
        
        # Complete items 1, 2, and 3 (5 from London, 2 from Boston)
        for item in [item1, item2, item3, item4]:
            progress = UserProgress(
                user_checklist_id=user_checklist.id,
                item_id=item.id,
                completed=(item.id in [item1.id, item2.id, item3.id])
            )
            db.session.add(progress)
        db.session.commit()
        
        # Check if item4 prerequisites are met
        # Should be met - 5 of 5 puzzle pieces from London
        are_met, unmet = item4.are_prerequisites_met(user_checklist.id)
        assert are_met, "Item should be unlocked - 5 of 5 puzzle pieces from London collected"
        assert len(unmet) == 0, "Should have no unmet prerequisites"


def test_reward_prerequisite_with_category_filter(app, authenticated_user):
    """Test that category-filtered reward prerequisites work correctly."""
    with app.app_context():
        # Create game and checklist
        game = Game(name='Test Game')
        db.session.add(game)
        db.session.commit()
        
        checklist = Checklist(
            title='Test Checklist',
            game_id=game.id,
            creator_id=authenticated_user,
            is_public=True
        )
        db.session.add(checklist)
        db.session.commit()
        
        # Create reward
        reward = Reward(name='Gem')
        db.session.add(reward)
        db.session.flush()
        
        # Create items with different categories
        item1 = ChecklistItem(checklist_id=checklist.id, title='Find Red Gem', category='Rare', order=1)
        item2 = ChecklistItem(checklist_id=checklist.id, title='Find Blue Gem', category='Common', order=2)
        item3 = ChecklistItem(checklist_id=checklist.id, title='Unlock Vault', order=3)
        db.session.add(item1)
        db.session.add(item2)
        db.session.add(item3)
        db.session.flush()
        
        # Add gems as rewards
        db.session.add(ItemReward(checklist_item_id=item1.id, reward_id=reward.id, amount=1))
        db.session.add(ItemReward(checklist_item_id=item2.id, reward_id=reward.id, amount=1))
        
        # Item 3 requires 1 rare gem
        prereq = ItemPrerequisite(
            item_id=item3.id,
            prerequisite_reward_id=reward.id,
            reward_amount=1,
            reward_category='Rare'
        )
        db.session.add(prereq)
        db.session.commit()
        
        # Create user checklist
        user_checklist = UserChecklist(user_id=authenticated_user, checklist_id=checklist.id)
        db.session.add(user_checklist)
        db.session.commit()
        
        # Complete only item2 (common gem)
        for item in [item1, item2, item3]:
            progress = UserProgress(
                user_checklist_id=user_checklist.id,
                item_id=item.id,
                completed=(item.id == item2.id)
            )
            db.session.add(progress)
        db.session.commit()
        
        # Check if item3 prerequisites are met
        # Should NOT be met - need rare gem, only have common gem
        are_met, unmet = item3.are_prerequisites_met(user_checklist.id)
        assert not are_met, "Item should be locked - need Rare gem but only have Common gem"
        assert len(unmet) == 1, "Should have 1 unmet prerequisite"


def test_toggle_progress_with_reward_prerequisite(client, app, authenticated_user):
    """Test that toggling progress respects reward prerequisites."""
    with app.app_context():
        # Create game and checklist
        game = Game(name='Test Game')
        db.session.add(game)
        db.session.commit()
        
        checklist = Checklist(
            title='Test Checklist',
            game_id=game.id,
            creator_id=authenticated_user,
            is_public=True
        )
        db.session.add(checklist)
        db.session.commit()
        
        # Create reward
        reward = Reward(name='Key')
        db.session.add(reward)
        db.session.flush()
        
        # Create items
        item1 = ChecklistItem(checklist_id=checklist.id, title='Find Key', order=1)
        item2 = ChecklistItem(checklist_id=checklist.id, title='Open Door', order=2)
        db.session.add(item1)
        db.session.add(item2)
        db.session.flush()
        
        # Item 1 gives a key
        db.session.add(ItemReward(checklist_item_id=item1.id, reward_id=reward.id, amount=1))
        
        # Item 2 requires 1 key
        prereq = ItemPrerequisite(
            item_id=item2.id,
            prerequisite_reward_id=reward.id,
            reward_amount=1
        )
        db.session.add(prereq)
        db.session.commit()
        
        # Create user checklist
        user_checklist = UserChecklist(user_id=authenticated_user, checklist_id=checklist.id)
        db.session.add(user_checklist)
        db.session.commit()
        
        # Create progress - both incomplete
        for item in [item1, item2]:
            progress = UserProgress(
                user_checklist_id=user_checklist.id,
                item_id=item.id,
                completed=False
            )
            db.session.add(progress)
        db.session.commit()
        
        item2_id = item2.id
    
    # Try to complete item2 without completing item1
    response = client.post(
        f'/checklist/1/progress/{item2_id}/toggle',
        content_type='application/json'
    )
    
    # Should fail - prerequisites not met
    assert response.status_code == 400
    data = response.get_json()
    assert data['success'] is False
    assert 'Prerequisites not met' in data['error']
