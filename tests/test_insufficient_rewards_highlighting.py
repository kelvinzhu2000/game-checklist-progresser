"""Tests for highlighting all consuming items when insufficient rewards are available."""

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


def test_insufficient_rewards_scenario(app, authenticated_user):
    """Test the scenario from the problem statement.
    
    Scenario:
    - Two items give 2 puzzle pieces each (total: 4 when both checked)
    - Two items consume puzzle pieces: one consumes 1, another consumes 2 (total: 3 consumed)
    - When one provider item is unchecked, available becomes 2 but consumed is still 3
    - Both consuming items should be flagged as problematic
    """
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
        puzzle_piece = Reward(name='Puzzle Piece')
        db.session.add(puzzle_piece)
        db.session.flush()
        
        # Item 1: Gives 2 puzzle pieces
        item1 = ChecklistItem(checklist_id=checklist.id, title='Provider 1', order=1)
        db.session.add(item1)
        db.session.flush()
        db.session.add(ItemReward(checklist_item_id=item1.id, reward_id=puzzle_piece.id, amount=2))
        
        # Item 2: Gives 2 puzzle pieces
        item2 = ChecklistItem(checklist_id=checklist.id, title='Provider 2', order=2)
        db.session.add(item2)
        db.session.flush()
        db.session.add(ItemReward(checklist_item_id=item2.id, reward_id=puzzle_piece.id, amount=2))
        
        # Item 3: Consumes 1 puzzle piece
        item3 = ChecklistItem(checklist_id=checklist.id, title='Consumer 1', order=3)
        db.session.add(item3)
        db.session.flush()
        prereq1 = ItemPrerequisite(
            item_id=item3.id,
            prerequisite_reward_id=puzzle_piece.id,
            reward_amount=1,
            consumes_reward=True
        )
        db.session.add(prereq1)
        
        # Item 4: Consumes 2 puzzle pieces
        item4 = ChecklistItem(checklist_id=checklist.id, title='Consumer 2', order=4)
        db.session.add(item4)
        db.session.flush()
        prereq2 = ItemPrerequisite(
            item_id=item4.id,
            prerequisite_reward_id=puzzle_piece.id,
            reward_amount=2,
            consumes_reward=True
        )
        db.session.add(prereq2)
        
        db.session.commit()
        
        # Create user checklist
        user_checklist = UserChecklist(user_id=authenticated_user, checklist_id=checklist.id)
        db.session.add(user_checklist)
        db.session.commit()
        
        # All items are completed initially
        progress1 = UserProgress(user_checklist_id=user_checklist.id, item_id=item1.id, completed=True)
        progress2 = UserProgress(user_checklist_id=user_checklist.id, item_id=item2.id, completed=True)
        progress3 = UserProgress(user_checklist_id=user_checklist.id, item_id=item3.id, completed=True)
        progress4 = UserProgress(user_checklist_id=user_checklist.id, item_id=item4.id, completed=True)
        db.session.add_all([progress1, progress2, progress3, progress4])
        db.session.commit()
        
        # Verify initial state - collected: 4, consumed: 3, available: 1
        collected = user_checklist.get_reward_tally(reward_id=puzzle_piece.id)
        consumed = user_checklist.get_consumed_rewards(reward_id=puzzle_piece.id)
        available = user_checklist.get_available_rewards(reward_id=puzzle_piece.id)
        
        assert collected == 4, f"Expected 4 collected, got {collected}"
        assert consumed == 3, f"Expected 3 consumed, got {consumed}"
        assert available == 1, f"Expected 1 available, got {available}"
        
        # Now uncheck one provider item (item1)
        progress1.completed = False
        db.session.commit()
        
        # Verify new state - collected: 2, consumed: 3, available: 0 (max(0, 2-3))
        collected = user_checklist.get_reward_tally(reward_id=puzzle_piece.id)
        consumed = user_checklist.get_consumed_rewards(reward_id=puzzle_piece.id)
        available = user_checklist.get_available_rewards(reward_id=puzzle_piece.id)
        
        assert collected == 2, f"Expected 2 collected, got {collected}"
        assert consumed == 3, f"Expected 3 consumed, got {consumed}"
        assert available == 0, f"Expected 0 available, got {available}"
        
        # The key test: Both consuming items should be flagged as problematic
        # We need a function that checks if there's insufficient rewards for ALL consuming items
        # This will be used by the frontend to apply red highlighting
        problematic_items = user_checklist.get_items_with_insufficient_rewards()
        problematic_item_ids = [item.id for item in problematic_items]
        
        # Both consuming items should be in the problematic list
        assert item3.id in problematic_item_ids, "Consumer 1 should be flagged as problematic"
        assert item4.id in problematic_item_ids, "Consumer 2 should be flagged as problematic"
        
        # Provider items should not be problematic
        assert item1.id not in problematic_item_ids, "Provider 1 should not be flagged"
        assert item2.id not in problematic_item_ids, "Provider 2 should not be flagged"


def test_insufficient_rewards_with_filters(app, authenticated_user):
    """Test insufficient rewards detection with location/category filters."""
    with app.app_context():
        # Create game and checklist
        game = Game(name='Test Game Filters')
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
        puzzle_piece = Reward(name='Puzzle Piece')
        db.session.add(puzzle_piece)
        db.session.flush()
        
        # Item 1: Gives 2 puzzle pieces in "Forest"
        item1 = ChecklistItem(checklist_id=checklist.id, title='Forest Provider', 
                             order=1, location='Forest')
        db.session.add(item1)
        db.session.flush()
        db.session.add(ItemReward(checklist_item_id=item1.id, reward_id=puzzle_piece.id, amount=2))
        
        # Item 2: Consumes 1 puzzle piece from "Forest"
        item2 = ChecklistItem(checklist_id=checklist.id, title='Forest Consumer 1', order=2)
        db.session.add(item2)
        db.session.flush()
        prereq1 = ItemPrerequisite(
            item_id=item2.id,
            prerequisite_reward_id=puzzle_piece.id,
            reward_amount=1,
            consumes_reward=True,
            reward_location='Forest'
        )
        db.session.add(prereq1)
        
        # Item 3: Consumes 2 puzzle pieces from "Forest"
        item3 = ChecklistItem(checklist_id=checklist.id, title='Forest Consumer 2', order=3)
        db.session.add(item3)
        db.session.flush()
        prereq2 = ItemPrerequisite(
            item_id=item3.id,
            prerequisite_reward_id=puzzle_piece.id,
            reward_amount=2,
            consumes_reward=True,
            reward_location='Forest'
        )
        db.session.add(prereq2)
        
        db.session.commit()
        
        # Create user checklist
        user_checklist = UserChecklist(user_id=authenticated_user, checklist_id=checklist.id)
        db.session.add(user_checklist)
        db.session.commit()
        
        # All items completed initially
        progress1 = UserProgress(user_checklist_id=user_checklist.id, item_id=item1.id, completed=True)
        progress2 = UserProgress(user_checklist_id=user_checklist.id, item_id=item2.id, completed=True)
        progress3 = UserProgress(user_checklist_id=user_checklist.id, item_id=item3.id, completed=True)
        db.session.add_all([progress1, progress2, progress3])
        db.session.commit()
        
        # Uncheck provider
        progress1.completed = False
        db.session.commit()
        
        # Both consumers should be problematic (collected: 0, consumed: 3 from Forest)
        problematic_items = user_checklist.get_items_with_insufficient_rewards()
        problematic_item_ids = [item.id for item in problematic_items]
        
        assert item2.id in problematic_item_ids, "Forest Consumer 1 should be flagged"
        assert item3.id in problematic_item_ids, "Forest Consumer 2 should be flagged"
