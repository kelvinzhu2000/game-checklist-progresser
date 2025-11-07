import sys
import os
from app import create_app, db
from app.models import User, Game, Checklist, ChecklistItem

app = create_app()
with app.app_context():
    # Create test user
    user = User(username='testuser2', email='testuser2@example.com')
    user.set_password('password123')
    db.session.add(user)
    
    # Create test game
    game = Game(name='Test Game')
    db.session.add(game)
    db.session.flush()
    
    # Create test checklist
    checklist = Checklist(
        title='My Test Checklist',
        game_id=game.id,
        description='Testing the new edit interface',
        creator_id=user.id,
        is_public=True
    )
    db.session.add(checklist)
    db.session.flush()
    
    # Add some items
    items = [
        ChecklistItem(checklist_id=checklist.id, title='Item 1', description='First item', order=1),
        ChecklistItem(checklist_id=checklist.id, title='Item 2', description='Second item', order=2),
        ChecklistItem(checklist_id=checklist.id, title='Item 3', description='Third item', order=3),
    ]
    for item in items:
        db.session.add(item)
    
    db.session.commit()
    
    print(f"Created user: {user.username} (ID: {user.id})")
    print(f"Created game: {game.name} (ID: {game.id})")
    print(f"Created checklist: {checklist.title} (ID: {checklist.id})")
    print(f"Added {len(items)} items")
    print(f"\nEdit URL: http://127.0.0.1:5000/checklist/{checklist.id}/edit")
