from app import create_app
from flask import session
import os

app = create_app()
app.config['SECRET_KEY'] = 'test-secret-key'

with app.test_request_context():
    # Login user 2
    with app.test_client() as client:
        client.post('/auth/login', data={
            'username': 'testuser2',
            'password': 'password123'
        })
        
        # Get session cookie
        cookie = None
        for cookie_obj in client.cookie_jar:
            if cookie_obj.name == 'session':
                cookie = cookie_obj
                break
        
        if cookie:
            print(f"Session cookie: {cookie.value}")
        else:
            print("No session cookie found")
