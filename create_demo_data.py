#!/usr/bin/env python
"""
Demo script to test category feature by creating test data in the database
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app, db
from app.models import User, Game, Checklist, ChecklistItem, UserChecklist, UserProgress

def create_demo_data():
    """Create demo data to showcase the category feature."""
    app = create_app()
    
    with app.app_context():
        # Create user
        user = User.query.filter_by(username='demo').first()
        if not user:
            user = User(username='demo', email='demo@example.com')
            user.set_password('demo123')
            db.session.add(user)
            db.session.commit()
            print("✓ Created demo user")
        else:
            print("✓ Demo user already exists")
        
        # Create game
        game = Game.query.filter_by(name='The Legend of Zelda: Breath of the Wild').first()
        if not game:
            game = Game(name='The Legend of Zelda: Breath of the Wild')
            db.session.add(game)
            db.session.commit()
            print("✓ Created game")
        else:
            print("✓ Game already exists")
        
        # Create checklist with categories
        checklist = Checklist.query.filter_by(title='100% Completion Guide', game_id=game.id).first()
        if not checklist:
            checklist = Checklist(
                title='100% Completion Guide',
                game_id=game.id,
                description='Complete guide for 100% completion with categorized items',
                creator_id=user.id,
                is_public=True
            )
            db.session.add(checklist)
            db.session.commit()
            print("✓ Created checklist")
        else:
            print("✓ Checklist already exists")
        
        # Create items with different categories
        items_data = [
            ('Defeat Ganon', 'Main Quest', 'Complete the final boss battle'),
            ('Free all Divine Beasts', 'Main Quest', 'Liberate all four Divine Beasts'),
            ('Collect all 120 Shrines', 'Shrines', 'Find and complete all 120 shrines'),
            ('Find all Shrine quests', 'Shrines', 'Complete all shrine-related quests'),
            ('Collect all 900 Korok Seeds', 'Collectibles', 'Find every Korok seed location'),
            ('Upgrade all armor', 'Armor', 'Fully upgrade all armor sets to max level'),
            ('Obtain Master Sword', 'Collectibles', 'Pull the Master Sword from the pedestal'),
            ('Complete all side quests', 'Side Quests', 'Finish all 76 side quests'),
            ('Complete all shrine quests', 'Side Quests', 'Finish all 42 shrine quests'),
            ('Collect all memories', 'Main Quest', 'Recover all 18 memories'),
            ('Defeat all Hinox', 'Enemies', 'Defeat all 40 Hinox in the game'),
            ('Defeat all Stone Talus', 'Enemies', 'Defeat all 40 Stone Talus'),
            ('Collect all medals of honor', 'Collectibles', 'Earn Hestu\'s medals'),
            ('Max out inventory', 'Collectibles', 'Expand all inventory slots'),
        ]
        
        existing_count = ChecklistItem.query.filter_by(checklist_id=checklist.id).count()
        if existing_count == 0:
            for idx, (title, category, description) in enumerate(items_data):
                item = ChecklistItem(
                    checklist_id=checklist.id,
                    title=title,
                    category=category,
                    description=description,
                    order=idx + 1
                )
                db.session.add(item)
            db.session.commit()
            print(f"✓ Created {len(items_data)} checklist items with categories")
        else:
            print(f"✓ Checklist already has {existing_count} items")
        
        # Create user copy with some progress
        user_checklist = UserChecklist.query.filter_by(
            user_id=user.id,
            checklist_id=checklist.id
        ).first()
        
        if not user_checklist:
            user_checklist = UserChecklist(
                user_id=user.id,
                checklist_id=checklist.id
            )
            db.session.add(user_checklist)
            db.session.commit()
            
            # Add progress for all items
            items = ChecklistItem.query.filter_by(checklist_id=checklist.id).all()
            for idx, item in enumerate(items):
                # Mark first 5 items as completed
                progress = UserProgress(
                    user_checklist_id=user_checklist.id,
                    item_id=item.id,
                    completed=(idx < 5)
                )
                db.session.add(progress)
            db.session.commit()
            print("✓ Created user copy with progress")
        else:
            print("✓ User copy already exists")
        
        print("\n" + "="*60)
        print("Demo data created successfully!")
        print("="*60)
        print(f"Username: demo")
        print(f"Password: demo123")
        print(f"Checklist ID: {checklist.id}")
        print(f"Checklist URL: http://127.0.0.1:5000/checklist/{checklist.id}")
        print("="*60)

if __name__ == '__main__':
    create_demo_data()
