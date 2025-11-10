#!/usr/bin/env python
"""
Create demo data specifically for testing the prerequisite consume flag issue.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app, db
from app.models import User, Game, Checklist, ChecklistItem, Reward, ItemPrerequisite, ItemReward

def create_consume_flag_demo():
    """Create demo data for testing consume flag persistence."""
    app = create_app()
    
    with app.app_context():
        # Create user
        user = User.query.filter_by(username='testuser').first()
        if not user:
            user = User(username='testuser', email='testuser@example.com')
            user.set_password('test123')
            db.session.add(user)
            db.session.flush()
        
        # Create game
        game = Game.query.filter_by(name='Test Game').first()
        if not game:
            game = Game(name='Test Game')
            db.session.add(game)
            db.session.flush()
        
        # Create checklist
        checklist = Checklist.query.filter_by(
            title='Consume Flag Test',
            creator_id=user.id
        ).first()
        
        if checklist:
            print("Demo data already exists! Deleting old data...")
            db.session.delete(checklist)
            db.session.commit()
        
        checklist = Checklist(
            title='Consume Flag Test',
            game_id=game.id,
            description='Test checklist for prerequisite consume flag persistence',
            creator_id=user.id,
            is_public=True
        )
        db.session.add(checklist)
        db.session.flush()
        
        # Create rewards
        gold_coin = Reward.query.filter_by(name='Gold Coin').first()
        if not gold_coin:
            gold_coin = Reward(name='Gold Coin')
            db.session.add(gold_coin)
            db.session.flush()
        
        silver_coin = Reward.query.filter_by(name='Silver Coin').first()
        if not silver_coin:
            silver_coin = Reward(name='Silver Coin')
            db.session.add(silver_coin)
            db.session.flush()
        
        # Item 1: Provides gold coins
        item1 = ChecklistItem(
            checklist_id=checklist.id,
            title='Collect Gold from Chest',
            description='Find the treasure chest and collect gold coins',
            location='Forest',
            category='Collection',
            order=1
        )
        db.session.add(item1)
        db.session.flush()
        
        # Add reward to item1
        item1_reward = ItemReward(
            checklist_item_id=item1.id,
            reward_id=gold_coin.id,
            amount=10
        )
        db.session.add(item1_reward)
        
        # Item 2: Provides silver coins
        item2 = ChecklistItem(
            checklist_id=checklist.id,
            title='Collect Silver from Chest',
            description='Find another chest with silver coins',
            location='Mountain',
            category='Collection',
            order=2
        )
        db.session.add(item2)
        db.session.flush()
        
        # Add reward to item2
        item2_reward = ItemReward(
            checklist_item_id=item2.id,
            reward_id=silver_coin.id,
            amount=5
        )
        db.session.add(item2_reward)
        
        # Item 3: Requires gold coins (consumes them)
        item3 = ChecklistItem(
            checklist_id=checklist.id,
            title='Buy Magic Sword',
            description='Purchase the magic sword from the blacksmith (costs 5 gold)',
            location='Village',
            category='Purchase',
            order=3
        )
        db.session.add(item3)
        db.session.flush()
        
        # Add prerequisite that CONSUMES gold coins
        prereq1 = ItemPrerequisite(
            item_id=item3.id,
            prerequisite_reward_id=gold_coin.id,
            reward_amount=5,
            consumes_reward=True  # THIS SHOULD PERSIST WHEN EDITING
        )
        db.session.add(prereq1)
        
        # Item 4: Requires gold coins (does NOT consume)
        item4 = ChecklistItem(
            checklist_id=checklist.id,
            title='Enter Rich District',
            description='Show proof of wealth to enter (need 3 gold, does not consume)',
            location='City',
            category='Access',
            order=4
        )
        db.session.add(item4)
        db.session.flush()
        
        # Add prerequisite that does NOT consume gold coins
        prereq2 = ItemPrerequisite(
            item_id=item4.id,
            prerequisite_reward_id=gold_coin.id,
            reward_amount=3,
            consumes_reward=False  # This should also persist
        )
        db.session.add(prereq2)
        
        # Item 5: Requires silver coins (consumes them)
        item5 = ChecklistItem(
            checklist_id=checklist.id,
            title='Buy Health Potion',
            description='Purchase a health potion (costs 2 silver)',
            location='Shop',
            category='Purchase',
            order=5
        )
        db.session.add(item5)
        db.session.flush()
        
        # Add prerequisite that CONSUMES silver coins
        prereq3 = ItemPrerequisite(
            item_id=item5.id,
            prerequisite_reward_id=silver_coin.id,
            reward_amount=2,
            consumes_reward=True
        )
        db.session.add(prereq3)
        
        db.session.commit()
        
        print(f"\n✅ Created demo checklist: '{checklist.title}'")
        print(f"  - {len(checklist.items.all())} items")
        print(f"  - User: {user.username}")
        print(f"  - Game: {game.name}")
        print("\nLogin credentials:")
        print("  Username: testuser")
        print("  Password: test123")
        print("\nTo test the consume flag fix:")
        print("1. Login and navigate to the checklist")
        print("2. Click 'Edit' on the checklist")
        print("3. DO NOT make any changes")
        print("4. Click 'Save Changes'")
        print("5. Check the database - consumes_reward should still be True for items 3 and 5")
        print("\nTo verify in the database:")
        print("  SELECT item_id, prerequisite_reward_id, reward_amount, consumes_reward")
        print("  FROM item_prerequisites WHERE consumes_reward = 1;")
        print(f"\nChecklist ID: {checklist.id}")
        print(f"Item 3 (Buy Magic Sword) ID: {item3.id}")
        print(f"Item 5 (Buy Health Potion) ID: {item5.id}")

if __name__ == '__main__':
    create_consume_flag_demo()
