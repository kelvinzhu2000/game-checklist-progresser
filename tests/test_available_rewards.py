"""Tests for available rewards calculation feature."""

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


def test_get_consumed_rewards_basic(app, authenticated_user):
    """Test basic consumed rewards calculation."""
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
        
        # Create items
        # Item 1: Gives 5 puzzle pieces
        item1 = ChecklistItem(checklist_id=checklist.id, title='Collect Puzzle', order=1)
        db.session.add(item1)
        db.session.flush()
        db.session.add(ItemReward(checklist_item_id=item1.id, reward_id=puzzle_piece.id, amount=5))
        
        # Item 2: Consumes 2 puzzle pieces
        item2 = ChecklistItem(checklist_id=checklist.id, title='Use Puzzle', order=2)
        db.session.add(item2)
        db.session.flush()
        prereq = ItemPrerequisite(
            item_id=item2.id,
            prerequisite_reward_id=puzzle_piece.id,
            reward_amount=2,
            consumes_reward=True
        )
        db.session.add(prereq)
        db.session.commit()
        
        # Create user checklist
        user_checklist = UserChecklist(user_id=authenticated_user, checklist_id=checklist.id)
        db.session.add(user_checklist)
        db.session.commit()
        
        # Create progress - both items completed
        progress1 = UserProgress(user_checklist_id=user_checklist.id, item_id=item1.id, completed=True)
        progress2 = UserProgress(user_checklist_id=user_checklist.id, item_id=item2.id, completed=True)
        db.session.add(progress1)
        db.session.add(progress2)
        db.session.commit()
        
        # Test consumed rewards - should be 2 puzzle pieces
        consumed = user_checklist.get_consumed_rewards(reward_id=puzzle_piece.id)
        assert consumed == 2, f"Expected 2 consumed puzzle pieces, got {consumed}"


def test_get_available_rewards_basic(app, authenticated_user):
    """Test basic available rewards calculation (collected - consumed)."""
    with app.app_context():
        # Create game and checklist
        game = Game(name='Test Game Available')
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
        
        # Create items
        # Item 1: Gives 5 puzzle pieces
        item1 = ChecklistItem(checklist_id=checklist.id, title='Collect Puzzle 1', order=1)
        db.session.add(item1)
        db.session.flush()
        db.session.add(ItemReward(checklist_item_id=item1.id, reward_id=puzzle_piece.id, amount=5))
        
        # Item 2: Gives 5 more puzzle pieces (total collected = 10)
        item2 = ChecklistItem(checklist_id=checklist.id, title='Collect Puzzle 2', order=2)
        db.session.add(item2)
        db.session.flush()
        db.session.add(ItemReward(checklist_item_id=item2.id, reward_id=puzzle_piece.id, amount=5))
        
        # Item 3: Consumes 2 puzzle pieces
        item3 = ChecklistItem(checklist_id=checklist.id, title='Use Puzzle 1', order=3)
        db.session.add(item3)
        db.session.flush()
        prereq1 = ItemPrerequisite(
            item_id=item3.id,
            prerequisite_reward_id=puzzle_piece.id,
            reward_amount=2,
            consumes_reward=True
        )
        db.session.add(prereq1)
        
        # Item 4: Consumes 2 more puzzle pieces (total consumed = 4)
        item4 = ChecklistItem(checklist_id=checklist.id, title='Use Puzzle 2', order=4)
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
        
        # Complete all items
        for item in [item1, item2, item3, item4]:
            progress = UserProgress(user_checklist_id=user_checklist.id, item_id=item.id, completed=True)
            db.session.add(progress)
        db.session.commit()
        
        # Test calculations
        collected = user_checklist.get_reward_tally(reward_id=puzzle_piece.id)
        consumed = user_checklist.get_consumed_rewards(reward_id=puzzle_piece.id)
        available = user_checklist.get_available_rewards(reward_id=puzzle_piece.id)
        
        assert collected == 10, f"Expected 10 collected puzzle pieces, got {collected}"
        assert consumed == 4, f"Expected 4 consumed puzzle pieces, got {consumed}"
        assert available == 6, f"Expected 6 available puzzle pieces (10 - 4), got {available}"


def test_get_available_rewards_with_filters(app, authenticated_user):
    """Test available rewards calculation with location/category filters."""
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
        star = Reward(name='Star')
        db.session.add(star)
        db.session.flush()
        
        # Create items with different locations
        # Item 1: Gives 3 stars in London
        item1 = ChecklistItem(checklist_id=checklist.id, title='London Star 1', location='London', order=1)
        db.session.add(item1)
        db.session.flush()
        db.session.add(ItemReward(checklist_item_id=item1.id, reward_id=star.id, amount=3))
        
        # Item 2: Gives 3 stars in Boston
        item2 = ChecklistItem(checklist_id=checklist.id, title='Boston Star 1', location='Boston', order=2)
        db.session.add(item2)
        db.session.flush()
        db.session.add(ItemReward(checklist_item_id=item2.id, reward_id=star.id, amount=3))
        
        # Item 3: Consumes 1 star from London specifically
        item3 = ChecklistItem(checklist_id=checklist.id, title='Use London Star', location='London', order=3)
        db.session.add(item3)
        db.session.flush()
        prereq = ItemPrerequisite(
            item_id=item3.id,
            prerequisite_reward_id=star.id,
            reward_amount=1,
            consumes_reward=True,
            reward_location='London'
        )
        db.session.add(prereq)
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
        
        # Test calculations with filters
        # London: collected 3, consumed 1, available 2
        london_collected = user_checklist.get_reward_tally(reward_id=star.id, location='London')
        london_consumed = user_checklist.get_consumed_rewards(reward_id=star.id, location='London')
        london_available = user_checklist.get_available_rewards(reward_id=star.id, location='London')
        
        assert london_collected == 3, f"Expected 3 collected London stars, got {london_collected}"
        assert london_consumed == 1, f"Expected 1 consumed London star, got {london_consumed}"
        assert london_available == 2, f"Expected 2 available London stars, got {london_available}"
        
        # Boston: collected 3, consumed 0, available 3
        boston_collected = user_checklist.get_reward_tally(reward_id=star.id, location='Boston')
        boston_consumed = user_checklist.get_consumed_rewards(reward_id=star.id, location='Boston')
        boston_available = user_checklist.get_available_rewards(reward_id=star.id, location='Boston')
        
        assert boston_collected == 3, f"Expected 3 collected Boston stars, got {boston_collected}"
        assert boston_consumed == 0, f"Expected 0 consumed Boston stars, got {boston_consumed}"
        assert boston_available == 3, f"Expected 3 available Boston stars, got {boston_available}"


def test_get_available_rewards_all_consumed(app, authenticated_user):
    """Test available rewards when all rewards are consumed."""
    with app.app_context():
        # Create game and checklist
        game = Game(name='Test Game All Consumed')
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
        coin = Reward(name='Coin')
        db.session.add(coin)
        db.session.flush()
        
        # Item 1: Gives 5 coins
        item1 = ChecklistItem(checklist_id=checklist.id, title='Collect Coins', order=1)
        db.session.add(item1)
        db.session.flush()
        db.session.add(ItemReward(checklist_item_id=item1.id, reward_id=coin.id, amount=5))
        
        # Item 2: Consumes 5 coins
        item2 = ChecklistItem(checklist_id=checklist.id, title='Use All Coins', order=2)
        db.session.add(item2)
        db.session.flush()
        prereq = ItemPrerequisite(
            item_id=item2.id,
            prerequisite_reward_id=coin.id,
            reward_amount=5,
            consumes_reward=True
        )
        db.session.add(prereq)
        db.session.commit()
        
        # Create user checklist
        user_checklist = UserChecklist(user_id=authenticated_user, checklist_id=checklist.id)
        db.session.add(user_checklist)
        db.session.commit()
        
        # Complete both items
        for item in [item1, item2]:
            progress = UserProgress(user_checklist_id=user_checklist.id, item_id=item.id, completed=True)
            db.session.add(progress)
        db.session.commit()
        
        # Test calculations
        collected = user_checklist.get_reward_tally(reward_id=coin.id)
        consumed = user_checklist.get_consumed_rewards(reward_id=coin.id)
        available = user_checklist.get_available_rewards(reward_id=coin.id)
        
        assert collected == 5, f"Expected 5 collected coins, got {collected}"
        assert consumed == 5, f"Expected 5 consumed coins, got {consumed}"
        assert available == 0, f"Expected 0 available coins (all consumed), got {available}"


def test_get_available_rewards_dict(app, authenticated_user):
    """Test getting all available rewards as a dictionary."""
    with app.app_context():
        # Create game and checklist
        game = Game(name='Test Game Dict')
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
        
        # Create rewards
        coin = Reward(name='Coin')
        gem = Reward(name='Gem')
        db.session.add(coin)
        db.session.add(gem)
        db.session.flush()
        
        # Item 1: Gives 10 coins
        item1 = ChecklistItem(checklist_id=checklist.id, title='Collect Coins', order=1)
        db.session.add(item1)
        db.session.flush()
        db.session.add(ItemReward(checklist_item_id=item1.id, reward_id=coin.id, amount=10))
        
        # Item 2: Gives 5 gems
        item2 = ChecklistItem(checklist_id=checklist.id, title='Collect Gems', order=2)
        db.session.add(item2)
        db.session.flush()
        db.session.add(ItemReward(checklist_item_id=item2.id, reward_id=gem.id, amount=5))
        
        # Item 3: Consumes 3 coins
        item3 = ChecklistItem(checklist_id=checklist.id, title='Use Coins', order=3)
        db.session.add(item3)
        db.session.flush()
        prereq1 = ItemPrerequisite(
            item_id=item3.id,
            prerequisite_reward_id=coin.id,
            reward_amount=3,
            consumes_reward=True
        )
        db.session.add(prereq1)
        
        # Item 4: Consumes 2 gems
        item4 = ChecklistItem(checklist_id=checklist.id, title='Use Gems', order=4)
        db.session.add(item4)
        db.session.flush()
        prereq2 = ItemPrerequisite(
            item_id=item4.id,
            prerequisite_reward_id=gem.id,
            reward_amount=2,
            consumes_reward=True
        )
        db.session.add(prereq2)
        db.session.commit()
        
        # Create user checklist
        user_checklist = UserChecklist(user_id=authenticated_user, checklist_id=checklist.id)
        db.session.add(user_checklist)
        db.session.commit()
        
        # Complete all items
        for item in [item1, item2, item3, item4]:
            progress = UserProgress(user_checklist_id=user_checklist.id, item_id=item.id, completed=True)
            db.session.add(progress)
        db.session.commit()
        
        # Test getting all available rewards as dict
        available_dict = user_checklist.get_available_rewards()
        
        assert coin.id in available_dict, "Coin should be in available rewards dict"
        assert gem.id in available_dict, "Gem should be in available rewards dict"
        assert available_dict[coin.id] == 7, f"Expected 7 available coins (10 - 3), got {available_dict[coin.id]}"
        assert available_dict[gem.id] == 3, f"Expected 3 available gems (5 - 2), got {available_dict[gem.id]}"


def test_non_consuming_prerequisites_dont_affect_available(app, authenticated_user):
    """Test that non-consuming prerequisites don't reduce available rewards."""
    with app.app_context():
        # Create game and checklist
        game = Game(name='Test Game Non-Consuming')
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
        key = Reward(name='Key')
        db.session.add(key)
        db.session.flush()
        
        # Item 1: Gives 1 key
        item1 = ChecklistItem(checklist_id=checklist.id, title='Find Key', order=1)
        db.session.add(item1)
        db.session.flush()
        db.session.add(ItemReward(checklist_item_id=item1.id, reward_id=key.id, amount=1))
        
        # Item 2: Requires 1 key but does NOT consume it
        item2 = ChecklistItem(checklist_id=checklist.id, title='Use Key (non-consuming)', order=2)
        db.session.add(item2)
        db.session.flush()
        prereq = ItemPrerequisite(
            item_id=item2.id,
            prerequisite_reward_id=key.id,
            reward_amount=1,
            consumes_reward=False  # Does not consume
        )
        db.session.add(prereq)
        db.session.commit()
        
        # Create user checklist
        user_checklist = UserChecklist(user_id=authenticated_user, checklist_id=checklist.id)
        db.session.add(user_checklist)
        db.session.commit()
        
        # Complete both items
        for item in [item1, item2]:
            progress = UserProgress(user_checklist_id=user_checklist.id, item_id=item.id, completed=True)
            db.session.add(progress)
        db.session.commit()
        
        # Test calculations - key should still be available since it wasn't consumed
        collected = user_checklist.get_reward_tally(reward_id=key.id)
        consumed = user_checklist.get_consumed_rewards(reward_id=key.id)
        available = user_checklist.get_available_rewards(reward_id=key.id)
        
        assert collected == 1, f"Expected 1 collected key, got {collected}"
        assert consumed == 0, f"Expected 0 consumed keys (non-consuming prerequisite), got {consumed}"
        assert available == 1, f"Expected 1 available key (not consumed), got {available}"
