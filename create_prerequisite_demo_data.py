#!/usr/bin/env python
"""
Create demo data for testing the prerequisite feature.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app, db
from app.models import User, Game, Checklist, ChecklistItem, UserChecklist, UserProgress, Reward, ItemPrerequisite

def create_demo_data():
    """Create demo data for prerequisite testing."""
    app = create_app()
    
    with app.app_context():
        # Create user
        user = User.query.filter_by(username='demo').first()
        if not user:
            user = User(username='demo', email='demo@example.com')
            user.set_password('demo123')
            db.session.add(user)
            db.session.flush()
        
        # Create game
        game = Game.query.filter_by(name='Zelda: Breath of the Wild').first()
        if not game:
            game = Game(name='Zelda: Breath of the Wild')
            db.session.add(game)
            db.session.flush()
        
        # Create checklist
        checklist = Checklist.query.filter_by(
            title='Divine Beasts Quest Line',
            creator_id=user.id
        ).first()
        
        if not checklist:
            checklist = Checklist(
                title='Divine Beasts Quest Line',
                game_id=game.id,
                description='Complete all Divine Beast quests with prerequisites',
                creator_id=user.id,
                is_public=True
            )
            db.session.add(checklist)
            db.session.flush()
            
            # Create rewards
            reward1 = Reward.query.filter_by(name='Heart Container').first()
            if not reward1:
                reward1 = Reward(name='Heart Container')
                db.session.add(reward1)
                db.session.flush()
            
            reward2 = Reward.query.filter_by(name='Champion Ability').first()
            if not reward2:
                reward2 = Reward(name='Champion Ability')
                db.session.add(reward2)
                db.session.flush()
            
            # Create items with prerequisites
            item1 = ChecklistItem(
                checklist_id=checklist.id,
                title='Visit Kakariko Village',
                description='Meet Impa and learn about the Divine Beasts',
                location='Kakariko Village',
                category='Main Quest',
                order=1
            )
            db.session.add(item1)
            db.session.flush()
            
            item2 = ChecklistItem(
                checklist_id=checklist.id,
                title='Visit Hateno Village',
                description='Complete the tech lab quest',
                location='Hateno Village',
                category='Main Quest',
                order=2
            )
            db.session.add(item2)
            db.session.flush()
            
            # This item requires the first two to be completed
            item3 = ChecklistItem(
                checklist_id=checklist.id,
                title='Free Vah Ruta',
                description='Defeat the Divine Beast in the Zora region',
                location='Zora\'s Domain',
                category='Divine Beast',
                order=3
            )
            db.session.add(item3)
            db.session.flush()
            
            # Add prerequisites for item3
            prereq1 = ItemPrerequisite(
                item_id=item3.id,
                prerequisite_item_id=item1.id
            )
            prereq2 = ItemPrerequisite(
                item_id=item3.id,
                prerequisite_item_id=item2.id
            )
            prereq3 = ItemPrerequisite(
                item_id=item3.id,
                freeform_text='Obtain 13 hearts'
            )
            db.session.add(prereq1)
            db.session.add(prereq2)
            db.session.add(prereq3)
            
            # Add reward to item3
            from app.models import ItemReward
            item_reward = ItemReward(
                checklist_item_id=item3.id,
                reward_id=reward1.id,
                amount=1
            )
            db.session.add(item_reward)
            
            item4 = ChecklistItem(
                checklist_id=checklist.id,
                title='Obtain Master Sword',
                description='Pull the Master Sword from its pedestal',
                location='Korok Forest',
                category='Legendary Weapon',
                order=4
            )
            db.session.add(item4)
            db.session.flush()
            
            # Master Sword requires heart containers
            prereq4 = ItemPrerequisite(
                item_id=item4.id,
                prerequisite_reward_id=reward1.id,
                consumes_reward=False  # Doesn't consume, but you need them
            )
            prereq5 = ItemPrerequisite(
                item_id=item4.id,
                freeform_text='13 total hearts required'
            )
            db.session.add(prereq4)
            db.session.add(prereq5)
            
            item5 = ChecklistItem(
                checklist_id=checklist.id,
                title='Free Vah Rudania',
                description='Defeat the Divine Beast on Death Mountain',
                location='Death Mountain',
                category='Divine Beast',
                order=5
            )
            db.session.add(item5)
            db.session.flush()
            
            # Rudania requires Vah Ruta and heat resistance
            prereq6 = ItemPrerequisite(
                item_id=item5.id,
                prerequisite_item_id=item3.id
            )
            prereq7 = ItemPrerequisite(
                item_id=item5.id,
                freeform_text='Fireproof armor or elixirs'
            )
            db.session.add(prereq6)
            db.session.add(prereq7)
            
            db.session.commit()
            
            print(f"Created demo checklist: '{checklist.title}'")
            print(f"  - {len(checklist.items.all())} items")
            print(f"  - User: {user.username}")
            print(f"  - Game: {game.name}")
            print("\nYou can login with:")
            print("  Username: demo")
            print("  Password: demo123")
        else:
            print("Demo data already exists!")

if __name__ == '__main__':
    create_demo_data()
