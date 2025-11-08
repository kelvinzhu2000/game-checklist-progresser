"""
Migration script to add 'rewards' table and 'checklist_item_rewards' association table.

This script creates the reward system for checklist items with a many-to-many relationship.
It also handles cleanup of the old game_name column if it still exists in the checklists table.

Run this script if you have an existing database that needs to be updated.

Usage:
    python add_reward_tables_migration.py
"""

import os
import sys

# Add the parent directory to the path so we can import the app
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app, db
from sqlalchemy import text

def migrate_database():
    """Add rewards and checklist_item_rewards tables if they don't exist.
    Also handle legacy game_name column cleanup."""
    app = create_app()
    
    with app.app_context():
        # Check if the tables already exist
        inspector = db.inspect(db.engine)
        existing_tables = inspector.get_table_names()
        
        rewards_exists = 'rewards' in existing_tables
        association_exists = 'checklist_item_rewards' in existing_tables
        
        # Check for legacy game_name column
        checklist_columns = [col['name'] for col in inspector.get_columns('checklists')]
        has_game_name = 'game_name' in checklist_columns
        has_game_id = 'game_id' in checklist_columns
        
        print("Database Status Check:")
        print(f"  - Rewards table exists: {rewards_exists}")
        print(f"  - Association table exists: {association_exists}")
        print(f"  - Checklists has game_id: {has_game_id}")
        print(f"  - Checklists has game_name: {has_game_name}")
        print()
        
        if rewards_exists and association_exists and not has_game_name:
            print("✓ Database is fully up to date. No migration needed.")
            return
        
        try:
            with db.engine.connect() as conn:
                # Handle legacy game_name column first
                if has_game_name and has_game_id:
                    print("Handling legacy game_name column...")
                    print("  Note: The game_name column is no longer used.")
                    print("  The application now uses game_id to reference the games table.")
                    print()
                    
                    # For SQLite, we need to recreate the table to drop a column
                    # This is a safe operation since we're keeping all the data
                    print("  Creating new checklists table without game_name...")
                    
                    # Create a new table with the correct schema
                    conn.execute(text('''
                        CREATE TABLE checklists_new (
                            id INTEGER PRIMARY KEY,
                            title VARCHAR(200) NOT NULL,
                            game_id INTEGER NOT NULL,
                            description TEXT,
                            creator_id INTEGER NOT NULL,
                            is_public BOOLEAN DEFAULT 1,
                            created_at DATETIME,
                            updated_at DATETIME,
                            FOREIGN KEY (game_id) REFERENCES games(id),
                            FOREIGN KEY (creator_id) REFERENCES users(id)
                        )
                    '''))
                    
                    # Copy data from old table to new table
                    print("  Copying data to new table...")
                    conn.execute(text('''
                        INSERT INTO checklists_new 
                            (id, title, game_id, description, creator_id, is_public, created_at, updated_at)
                        SELECT 
                            id, title, game_id, description, creator_id, is_public, created_at, updated_at
                        FROM checklists
                    '''))
                    
                    # Drop old table
                    print("  Dropping old table...")
                    conn.execute(text('DROP TABLE checklists'))
                    
                    # Rename new table
                    print("  Renaming new table...")
                    conn.execute(text('ALTER TABLE checklists_new RENAME TO checklists'))
                    
                    # Recreate indexes
                    print("  Recreating indexes...")
                    conn.execute(text('CREATE INDEX ix_checklists_game_id ON checklists(game_id)'))
                    conn.execute(text('CREATE INDEX ix_checklists_is_public ON checklists(is_public)'))
                    
                    print("  ✓ Successfully removed game_name column.")
                    print()
                
                # Create rewards table if it doesn't exist
                if not rewards_exists:
                    print("Creating 'rewards' table...")
                    conn.execute(text('''
                        CREATE TABLE rewards (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            name VARCHAR(100) NOT NULL UNIQUE,
                            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                        )
                    '''))
                    conn.execute(text('CREATE INDEX ix_rewards_name ON rewards (name)'))
                    print("  ✓ Created 'rewards' table.")
                
                # Create association table if it doesn't exist
                if not association_exists:
                    print("Creating 'checklist_item_rewards' association table...")
                    conn.execute(text('''
                        CREATE TABLE checklist_item_rewards (
                            checklist_item_id INTEGER NOT NULL,
                            reward_id INTEGER NOT NULL,
                            PRIMARY KEY (checklist_item_id, reward_id),
                            FOREIGN KEY (checklist_item_id) REFERENCES checklist_items (id),
                            FOREIGN KEY (reward_id) REFERENCES rewards (id)
                        )
                    '''))
                    print("  ✓ Created 'checklist_item_rewards' association table.")
                
                conn.commit()
            
            print()
            print("✓ Migration completed successfully!")
            print("  - Reward system tables are ready")
            if has_game_name:
                print("  - Legacy game_name column removed")
            print("  You can now use the reward features in the application.")
            
        except Exception as e:
            print(f"\n✗ Error during migration: {e}")
            print("\nIf you see errors about existing tables, your database may already be migrated.")
            print("If you have the game_name column issue, please run 'python migrate_to_game_model.py' first.")
            sys.exit(1)

if __name__ == '__main__':
    print("=" * 60)
    print("Database Migration: Add Reward System Tables")
    print("=" * 60)
    print()
    
    migrate_database()
    
    print()
    print("Migration completed successfully!")
    print("=" * 60)
