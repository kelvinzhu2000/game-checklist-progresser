#!/usr/bin/env python
"""
Migration script to add reward_amount column to item_prerequisites table.

This script adds the reward_amount field to support specifying amounts for reward prerequisites.
"""

import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app, db

def migrate():
    """Run the migration."""
    app = create_app()
    
    with app.app_context():
        print("Adding reward_amount column to item_prerequisites table...")
        
        # Add the column using raw SQL for SQLite compatibility
        try:
            with db.engine.connect() as conn:
                conn.execute(db.text("ALTER TABLE item_prerequisites ADD COLUMN reward_amount INTEGER DEFAULT 1"))
                conn.commit()
            print("Migration completed successfully!")
            print("The reward_amount column has been added to item_prerequisites table.")
        except Exception as e:
            if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                print("Column already exists. No migration needed.")
            else:
                print(f"Error during migration: {e}")
                raise

if __name__ == '__main__':
    migrate()
