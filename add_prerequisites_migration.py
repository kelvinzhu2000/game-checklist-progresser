#!/usr/bin/env python
"""
Migration script to add prerequisites table.

This script adds the item_prerequisites table to support prerequisite functionality.
"""

import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app, db
from app.models import ItemPrerequisite

def migrate():
    """Run the migration."""
    app = create_app()
    
    with app.app_context():
        print("Creating item_prerequisites table...")
        
        # Create the table using SQLAlchemy
        db.create_all()
        
        print("Migration completed successfully!")
        print("The item_prerequisites table has been created.")

if __name__ == '__main__':
    migrate()
