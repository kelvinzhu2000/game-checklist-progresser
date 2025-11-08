"""
Migration script to add 'rewards' table and 'checklist_item_rewards' association table.

This script creates the reward system for checklist items with a many-to-many relationship.
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
    """Add rewards and checklist_item_rewards tables if they don't exist."""
    app = create_app()
    
    with app.app_context():
        # Check if the tables already exist
        inspector = db.inspect(db.engine)
        existing_tables = inspector.get_table_names()
        
        rewards_exists = 'rewards' in existing_tables
        association_exists = 'checklist_item_rewards' in existing_tables
        
        if rewards_exists and association_exists:
            print("✓ Reward tables already exist.")
            return
        
        print("Creating reward system tables...")
        
        try:
            with db.engine.connect() as conn:
                # Create rewards table if it doesn't exist
                if not rewards_exists:
                    print("  Creating 'rewards' table...")
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
                    print("  Creating 'checklist_item_rewards' association table...")
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
            
            print("✓ Successfully created reward system tables.")
            print("  You can now assign rewards to checklist items through the UI.")
            
        except Exception as e:
            print(f"✗ Error creating reward tables: {e}")
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
