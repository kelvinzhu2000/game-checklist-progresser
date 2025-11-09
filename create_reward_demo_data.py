"""
Create demo data for testing the reward system.
"""
import os
import sys

# Add the parent directory to the path so we can import the app
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app, db
from app.models import User, Game, Checklist, ChecklistItem, Reward, ItemReward

def create_demo_data():
    """Create demo data for reward system testing."""
    app = create_app()
    
    with app.app_context():
        # Check if demo user already exists
        demo_user = User.query.filter_by(username='rewarddemo').first()
        if demo_user:
            print("Demo data already exists. Skipping creation.")
            return
        
        print("Creating demo data for reward system...")
        
        # Create demo user
        demo_user = User(username='rewarddemo', email='rewarddemo@example.com')
        demo_user.set_password('demo123')
        db.session.add(demo_user)
        db.session.commit()
        print("✓ Created demo user: rewarddemo / demo123")
        
        # Create or get game
        game = Game.query.filter_by(name='The Legend of Zelda: Tears of the Kingdom').first()
        if not game:
            game = Game(name='The Legend of Zelda: Tears of the Kingdom')
            db.session.add(game)
            db.session.commit()
        print(f"✓ Using game: {game.name}")
        
        # Create checklist
        checklist = Checklist(
            title='Complete Adventure Guide',
            game_id=game.id,
            creator_id=demo_user.id,
            description='A comprehensive guide to completing all the major objectives in the game with various rewards.',
            is_public=True
        )
        db.session.add(checklist)
        db.session.commit()
        print(f"✓ Created checklist: {checklist.title}")
        
        # Create rewards
        rewards_data = [
            'Heart Container',
            'Stamina Vessel',
            'Rare Ore',
            'Ancient Parts',
            'Champion Ability',
            'Unique Weapon',
            'Armor Set',
            'Rupees',
            'Spirit Orb',
            'Korok Seed'
        ]
        
        rewards_dict = {}
        for reward_name in rewards_data:
            reward = Reward(name=reward_name)
            db.session.add(reward)
            db.session.flush()
            rewards_dict[reward_name] = reward
        print(f"✓ Created {len(rewards_dict)} reward types")
        
        # Create checklist items with various rewards
        items_data = [
            {
                'title': 'Complete Divine Beast Vah Ruta',
                'description': 'Defeat Waterblight Ganon and free Vah Ruta',
                'category': 'Main Quest',
                'rewards': ['Heart Container', 'Champion Ability']
            },
            {
                'title': 'Complete Divine Beast Vah Rudania',
                'description': 'Defeat Fireblight Ganon and free Vah Rudania',
                'category': 'Main Quest',
                'rewards': ['Heart Container', 'Champion Ability']
            },
            {
                'title': 'Upgrade Master Sword',
                'description': 'Complete the Trial of the Sword',
                'category': 'Side Quest',
                'rewards': ['Unique Weapon']
            },
            {
                'title': 'Find Hestu',
                'description': 'Locate Hestu and expand inventory',
                'category': 'Side Quest',
                'rewards': ['Korok Seed']
            },
            {
                'title': 'Complete Shrine: Oman Au',
                'description': 'Solve the Magnesis Trial shrine',
                'category': 'Shrine',
                'rewards': ['Spirit Orb']
            },
            {
                'title': 'Complete Shrine: Ja Baij',
                'description': 'Solve the Bomb Trial shrine',
                'category': 'Shrine',
                'rewards': ['Spirit Orb']
            },
            {
                'title': 'Find Climbing Gear Set',
                'description': 'Locate all pieces of the Climbing Set',
                'category': 'Collectibles',
                'rewards': ['Armor Set']
            },
            {
                'title': 'Mine Rare Ore at Death Mountain',
                'description': 'Collect rare gems from ore deposits',
                'category': 'Collectibles',
                'rewards': ['Rare Ore', 'Rupees']
            },
            {
                'title': 'Defeat Guardian Stalker',
                'description': 'Successfully destroy a Guardian Stalker',
                'category': 'Combat',
                'rewards': ['Ancient Parts', 'Rupees']
            },
            {
                'title': 'Complete Eventide Island',
                'description': 'Survive the trial on Eventide Island',
                'category': 'Challenge',
                'rewards': ['Spirit Orb', 'Rupees']
            },
            {
                'title': 'Unlock All Towers',
                'description': 'Activate all 15 Sheikah Towers',
                'category': 'Exploration',
                'rewards': []
            },
            {
                'title': 'Complete Tarrey Town',
                'description': 'Build and complete Tarrey Town',
                'category': 'Side Quest',
                'rewards': ['Rupees', 'Unique Weapon']
            },
            {
                'title': 'Trade with Kilton',
                'description': 'Exchange Mon for unique items',
                'category': 'Side Quest',
                'rewards': ['Armor Set']
            },
            {
                'title': 'Complete All Labyrinths',
                'description': 'Navigate and complete the three labyrinths',
                'category': 'Challenge',
                'rewards': ['Armor Set', 'Spirit Orb']
            }
        ]
        
        for idx, item_data in enumerate(items_data, 1):
            item = ChecklistItem(
                checklist_id=checklist.id,
                title=item_data['title'],
                description=item_data.get('description', ''),
                category=item_data.get('category', ''),
                order=idx
            )
            db.session.add(item)
            db.session.flush()
            
            # Add rewards to item using ItemReward
            for reward_name in item_data.get('rewards', []):
                if reward_name in rewards_dict:
                    item_reward = ItemReward(
                        checklist_item_id=item.id,
                        reward_id=rewards_dict[reward_name].id,
                        amount=1
                    )
                    db.session.add(item_reward)
        
        db.session.commit()
        print(f"✓ Created {len(items_data)} checklist items with rewards")
        
        print("\n" + "="*60)
        print("Demo data created successfully!")
        print("="*60)
        print(f"Username: rewarddemo")
        print(f"Password: demo123")
        print(f"Game: {game.name}")
        print(f"Checklist: {checklist.title}")
        print("="*60)

if __name__ == '__main__':
    create_demo_data()
