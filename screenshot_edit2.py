from app import create_app
import sys

app = create_app()
app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for testing

# Create test client
client = app.test_client()

# Login
with app.app_context():
    response = client.post('/auth/login', data={
        'username': 'testuser2',
        'password': 'password123'
    }, follow_redirects=False)
    
    print("Login response status:", response.status_code)
    
    # Now get the edit page
    response = client.get('/checklist/1/edit', follow_redirects=True)
    print("\nEdit page status:", response.status_code)
    
    # Save HTML to file for inspection
    with open('/tmp/edit_page.html', 'wb') as f:
        f.write(response.data)
    print("Edit page HTML saved to /tmp/edit_page.html")
    
    # Check if our new elements are present
    html = response.data.decode('utf-8')
    if 'Checklist Items' in html:
        print("\n✓ 'Checklist Items' section found")
    if 'editable-item' in html:
        print("✓ Editable item divs found")
    if 'Add Item' in html:
        print("✓ 'Add Item' button found")
    if 'saveChanges' in html:
        print("✓ 'Save Changes' function found")
    if 'Item 1' in html:
        print("✓ First item ('Item 1') found in edit page")
