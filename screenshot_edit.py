from flask import Flask
from app import create_app, db
from app.models import User
import sys

app = create_app()

# Create test client
client = app.test_client()

# Login
with app.app_context():
    response = client.post('/auth/login', data={
        'username': 'testuser2',
        'password': 'password123'
    }, follow_redirects=True)
    
    print("Login response status:", response.status_code)
    if b'Login successful' in response.data or b'testuser2' in response.data:
        print("Login successful!")
        
        # Now get the edit page
        response = client.get('/checklist/1/edit')
        print("\nEdit page status:", response.status_code)
        
        # Save HTML to file for inspection
        with open('/tmp/edit_page.html', 'wb') as f:
            f.write(response.data)
        print("Edit page HTML saved to /tmp/edit_page.html")
        
        # Check if our new elements are present
        if b'Checklist Items' in response.data:
            print("\n✓ 'Checklist Items' section found")
        if b'editable-item' in response.data:
            print("✓ Editable item divs found")
        if b'Add Item' in response.data:
            print("✓ 'Add Item' button found")
        if b'saveChanges' in response.data:
            print("✓ 'Save Changes' function found")
    else:
        print("Login failed!")
        print(response.data.decode('utf-8'))
