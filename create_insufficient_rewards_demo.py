"""Create demo data to test the insufficient rewards highlighting feature."""

from app import create_app, db
from app.models import User, Game, Checklist, ChecklistItem, UserChecklist, UserProgress, Reward, ItemReward, ItemPrerequisite
from datetime import datetime

def create_demo_data():
    app = create_app()
    
    with app.app_context():
        # Create or get test user
        user = User.query.filter_by(username='testuser').first()
        if not user:
            user = User(username='testuser', email='test@example.com')
            user.set_password('password')
            db.session.add(user)
            db.session.flush()
        
        # Create game
        game = Game.query.filter_by(name='Puzzle Game').first()
        if not game:
            game = Game(name='Puzzle Game')
            db.session.add(game)
            db.session.flush()
        
        # Create checklist
        checklist = Checklist(
            title='Insufficient Rewards Demo',
            game_id=game.id,
            creator_id=user.id,
            is_public=True,
            description='Demo checklist to showcase insufficient rewards highlighting'
        )
        db.session.add(checklist)
        db.session.flush()
        
        # Create reward
        puzzle_piece = Reward.query.filter_by(name='Puzzle Piece').first()
        if not puzzle_piece:
            puzzle_piece = Reward(name='Puzzle Piece')
            db.session.add(puzzle_piece)
            db.session.flush()
        
        # Create items
        # Item 1: Provider - gives 2 puzzle pieces
        item1 = ChecklistItem(
            checklist_id=checklist.id,
            title='Find First Puzzle Cache',
            description='Collect 2 puzzle pieces from the forest',
            location='Forest',
            order=1
        )
        db.session.add(item1)
        db.session.flush()
        db.session.add(ItemReward(checklist_item_id=item1.id, reward_id=puzzle_piece.id, amount=2))
        
        # Item 2: Provider - gives 2 puzzle pieces
        item2 = ChecklistItem(
            checklist_id=checklist.id,
            title='Find Second Puzzle Cache',
            description='Collect 2 puzzle pieces from the cave',
            location='Cave',
            order=2
        )
        db.session.add(item2)
        db.session.flush()
        db.session.add(ItemReward(checklist_item_id=item2.id, reward_id=puzzle_piece.id, amount=2))
        
        # Item 3: Consumer - consumes 1 puzzle piece
        item3 = ChecklistItem(
            checklist_id=checklist.id,
            title='Unlock Small Door',
            description='Uses 1 puzzle piece to unlock a small door',
            location='Temple',
            order=3
        )
        db.session.add(item3)
        db.session.flush()
        prereq1 = ItemPrerequisite(
            item_id=item3.id,
            prerequisite_reward_id=puzzle_piece.id,
            reward_amount=1,
            consumes_reward=True
        )
        db.session.add(prereq1)
        
        # Item 4: Consumer - consumes 2 puzzle pieces
        item4 = ChecklistItem(
            checklist_id=checklist.id,
            title='Unlock Large Gate',
            description='Uses 2 puzzle pieces to unlock a large gate',
            location='Castle',
            order=4
        )
        db.session.add(item4)
        db.session.flush()
        prereq2 = ItemPrerequisite(
            item_id=item4.id,
            prerequisite_reward_id=puzzle_piece.id,
            reward_amount=2,
            consumes_reward=True
        )
        db.session.add(prereq2)
        
        # Item 5: Regular item (no rewards, no prerequisites)
        item5 = ChecklistItem(
            checklist_id=checklist.id,
            title='Explore the Garden',
            description='A regular task with no rewards or prerequisites',
            location='Garden',
            order=5
        )
        db.session.add(item5)
        db.session.flush()
        
        db.session.commit()
        
        # Create user checklist
        user_checklist = UserChecklist(user_id=user.id, checklist_id=checklist.id)
        db.session.add(user_checklist)
        db.session.flush()
        
        # Create progress entries - all items completed initially
        # This represents the scenario: 4 puzzle pieces collected, 3 consumed
        progress1 = UserProgress(user_checklist_id=user_checklist.id, item_id=item1.id, completed=True)
        progress2 = UserProgress(user_checklist_id=user_checklist.id, item_id=item2.id, completed=True)
        progress3 = UserProgress(user_checklist_id=user_checklist.id, item_id=item3.id, completed=True)
        progress4 = UserProgress(user_checklist_id=user_checklist.id, item_id=item4.id, completed=True)
        progress5 = UserProgress(user_checklist_id=user_checklist.id, item_id=item5.id, completed=False)
        
        db.session.add_all([progress1, progress2, progress3, progress4, progress5])
        db.session.commit()
        
        print(f"Demo data created successfully!")
        print(f"Game: {game.name}")
        print(f"Checklist: {checklist.title}")
        print(f"User: {user.username} (password: password)")
        print(f"\nInitial state:")
        print(f"  - Item 1 (Provider): ✓ Gives 2 puzzle pieces")
        print(f"  - Item 2 (Provider): ✓ Gives 2 puzzle pieces")
        print(f"  - Item 3 (Consumer): ✓ Consumes 1 puzzle piece")
        print(f"  - Item 4 (Consumer): ✓ Consumes 2 puzzle pieces")
        print(f"  - Total collected: 4, Total consumed: 3, Available: 1")
        print(f"\nTo test the feature:")
        print(f"  1. Log in as 'testuser' / 'password'")
        print(f"  2. Navigate to the checklist")
        print(f"  3. Uncheck either Item 1 or Item 2 (provider)")
        print(f"  4. Both consuming items (3 and 4) should turn RED")
        print(f"  5. Recheck the provider item - red highlighting should disappear")

if __name__ == '__main__':
    create_demo_data()
