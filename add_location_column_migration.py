#!/usr/bin/env python
"""
Migration script to add location column to checklist_items table.
This script adds an optional location field to checklist items.
"""

import sys
import os

# Add the parent directory to the path to import app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from app import create_app, db
from sqlalchemy import text

def add_location_column():
    """Add location column to checklist_items table."""
    app = create_app()
    
    with app.app_context():
        try:
            # Check if the column already exists
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('checklist_items')]
            
            if 'location' in columns:
                print("Location column already exists in checklist_items table.")
                return
            
            # Add the location column
            print("Adding location column to checklist_items table...")
            with db.engine.connect() as conn:
                conn.execute(text('ALTER TABLE checklist_items ADD COLUMN location VARCHAR(100)'))
                conn.commit()
            
            print("✓ Successfully added location column to checklist_items table")
            
        except Exception as e:
            print(f"✗ Error during migration: {str(e)}")
            raise

if __name__ == '__main__':
    add_location_column()
