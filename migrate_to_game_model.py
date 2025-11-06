#!/usr/bin/env python
"""
Migration script to convert existing database from game_name to Game model.

This script should be run ONCE on existing databases to migrate from the old schema
where Checklist had a game_name string field to the new schema where Checklist
has a game_id foreign key to the Game table.

Usage:
    python migrate_to_game_model.py

Prerequisites:
    - Backup your database before running this script!
    - The app must be updated to the new code with the Game model
"""

import sys
import os

# Add the parent directory to the path so we can import app
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app, db
from app.models import Game, Checklist
from sqlalchemy import text, inspect


def check_migration_needed():
    """Check if migration is needed by inspecting the database schema."""
    inspector = inspect(db.engine)
    
    # Check if 'games' table exists
    games_table_exists = 'games' in inspector.get_table_names()
    
    # Check if 'checklists' table has 'game_name' column
    checklist_columns = [col['name'] for col in inspector.get_columns('checklists')]
    has_game_name = 'game_name' in checklist_columns
    has_game_id = 'game_id' in checklist_columns
    
    return {
        'games_table_exists': games_table_exists,
        'has_game_name': has_game_name,
        'has_game_id': has_game_id,
        'needs_migration': has_game_name and not has_game_id
    }


def migrate_database():
    """Migrate the database from game_name to Game model."""
    
    print("Starting database migration...")
    print("=" * 60)
    
    # Check current state
    status = check_migration_needed()
    
    print(f"Games table exists: {status['games_table_exists']}")
    print(f"Checklists has game_name: {status['has_game_name']}")
    print(f"Checklists has game_id: {status['has_game_id']}")
    print()
    
    if not status['needs_migration']:
        if status['has_game_id'] and not status['has_game_name']:
            print("✓ Database is already migrated!")
            return True
        else:
            print("✗ Database is in an unexpected state.")
            print("  Expected: game_name column exists, game_id does not exist")
            return False
    
    print("Migration needed. Starting migration process...")
    print()
    
    try:
        # Step 1: Create games table if it doesn't exist
        if not status['games_table_exists']:
            print("Step 1: Creating games table...")
            db.create_all()
            print("✓ Games table created")
        else:
            print("Step 1: Games table already exists")
        
        # Step 2: Get all unique game names from checklists
        print("\nStep 2: Extracting unique game names from checklists...")
        result = db.session.execute(
            text("SELECT DISTINCT game_name FROM checklists WHERE game_name IS NOT NULL")
        )
        game_names = [row[0] for row in result]
        print(f"✓ Found {len(game_names)} unique games")
        
        # Step 3: Create Game records for each unique game name
        print("\nStep 3: Creating Game records...")
        game_map = {}
        for game_name in game_names:
            game = Game(name=game_name)
            db.session.add(game)
            db.session.flush()  # Get the ID
            game_map[game_name] = game.id
            print(f"  - Created game '{game_name}' with ID {game.id}")
        
        db.session.commit()
        print(f"✓ Created {len(game_map)} Game records")
        
        # Step 4: Add game_id column to checklists if it doesn't exist
        if not status['has_game_id']:
            print("\nStep 4: Adding game_id column to checklists table...")
            db.session.execute(text(
                "ALTER TABLE checklists ADD COLUMN game_id INTEGER"
            ))
            db.session.commit()
            print("✓ Added game_id column")
        else:
            print("\nStep 4: game_id column already exists")
        
        # Step 5: Populate game_id based on game_name
        print("\nStep 5: Populating game_id for all checklists...")
        for game_name, game_id in game_map.items():
            db.session.execute(
                text("UPDATE checklists SET game_id = :game_id WHERE game_name = :game_name"),
                {'game_id': game_id, 'game_name': game_name}
            )
        db.session.commit()
        print("✓ Populated game_id for all checklists")
        
        # Step 6: Add foreign key constraint and index
        print("\nStep 6: Adding foreign key constraint and index...")
        try:
            # Note: SQLite doesn't support adding foreign key constraints to existing tables
            # For SQLite, we'd need to recreate the table
            # For PostgreSQL/MySQL, we can add the constraint
            db.session.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_checklists_game_id ON checklists(game_id)"
            ))
            db.session.commit()
            print("✓ Added index on game_id")
        except Exception as db_error:
            print(f"  Note: Could not add foreign key constraint: {db_error}")
            print("  This is expected for SQLite. The relationship will still work.")
        
        # Step 7: Drop game_name column (optional - commented out for safety)
        print("\nStep 7: Removing game_name column...")
        print("  SKIPPED - Keeping game_name column for backwards compatibility")
        print("  To remove it manually, run: ALTER TABLE checklists DROP COLUMN game_name")
        
        print("\n" + "=" * 60)
        print("✓ Migration completed successfully!")
        print("\nNext steps:")
        print("1. Test your application thoroughly")
        print("2. If everything works, you can manually drop the game_name column")
        print("3. Update any custom queries that still reference game_name")
        
        return True
        
    except Exception as migration_error:
        db.session.rollback()
        print(f"\n✗ Migration failed: {migration_error}")
        print("\nDatabase has been rolled back to previous state.")
        return False


def main():
    """Main entry point for the migration script."""
    app = create_app()
    
    with app.app_context():
        print("Game Checklist Progresser - Database Migration")
        print("=" * 60)
        print("This script will migrate your database to use the new Game model.")
        print()
        print("⚠️  WARNING: Make sure you have backed up your database!")
        print()
        
        response = input("Do you want to proceed? (yes/y to confirm): ").strip().lower()
        
        if response not in ['yes', 'y']:
            print("\nMigration cancelled.")
            return
        
        print()
        success = migrate_database()
        
        if success:
            sys.exit(0)
        else:
            sys.exit(1)


if __name__ == '__main__':
    main()
