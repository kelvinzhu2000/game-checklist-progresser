"""
Migration script to add 'category' column to checklist_items table.

This script adds a new optional 'category' field to existing ChecklistItem records.
Run this script if you have an existing database that needs to be updated.

Usage:
    python add_category_column_migration.py
"""

import os
import sys

# Add the parent directory to the path so we can import the app
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app, db
from app.models import ChecklistItem
from sqlalchemy import text

def migrate_database():
    """Add category column to checklist_items table if it doesn't exist."""
    app = create_app()
    
    with app.app_context():
        # Check if the column already exists
        inspector = db.inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('checklist_items')]
        
        if 'category' in columns:
            print("✓ Category column already exists in checklist_items table.")
            return
        
        print("Adding 'category' column to checklist_items table...")
        
        try:
            # Add the category column
            with db.engine.connect() as conn:
                conn.execute(text('ALTER TABLE checklist_items ADD COLUMN category VARCHAR(100)'))
                conn.commit()
            
            print("✓ Successfully added 'category' column to checklist_items table.")
            print("  All existing items will have NULL category values.")
            print("  You can now assign categories to items through the UI.")
            
        except Exception as e:
            print(f"✗ Error adding category column: {e}")
            sys.exit(1)

if __name__ == '__main__':
    print("=" * 60)
    print("Database Migration: Add Category Column to ChecklistItem")
    print("=" * 60)
    print()
    
    migrate_database()
    
    print()
    print("Migration completed successfully!")
    print("=" * 60)
