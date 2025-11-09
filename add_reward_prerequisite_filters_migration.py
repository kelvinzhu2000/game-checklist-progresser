#!/usr/bin/env python
"""
Migration script to add reward_location and reward_category columns to item_prerequisites table.
This allows filtering reward prerequisites by location and/or category.
"""

import sys
import os

# Add the parent directory to the path to import app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from app import create_app, db
from sqlalchemy import text

def add_reward_prerequisite_filter_columns():
    """Add reward_location and reward_category columns to item_prerequisites table."""
    app = create_app()
    
    with app.app_context():
        try:
            # Check if the columns already exist
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('item_prerequisites')]
            
            columns_to_add = []
            if 'reward_location' not in columns:
                columns_to_add.append('reward_location')
            if 'reward_category' not in columns:
                columns_to_add.append('reward_category')
            
            if not columns_to_add:
                print("Reward location and category columns already exist in item_prerequisites table.")
                return
            
            # Add the columns
            with db.engine.connect() as conn:
                for column in columns_to_add:
                    print(f"Adding {column} column to item_prerequisites table...")
                    conn.execute(text(f'ALTER TABLE item_prerequisites ADD COLUMN {column} VARCHAR(100)'))
                conn.commit()
            
            print("✓ Successfully added reward filter columns to item_prerequisites table")
            
        except Exception as e:
            print(f"✗ Error during migration: {str(e)}")
            raise

if __name__ == '__main__':
    add_reward_prerequisite_filter_columns()
