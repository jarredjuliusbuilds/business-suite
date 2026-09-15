from app import create_app
from app.models import User, Business
from app.extensions import db
import warnings
warnings.filterwarnings('ignore')

app = create_app()
app.config['PROPAGATE_EXCEPTIONS'] = True
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test_debug3.db'

with app.app_context():
    db.create_all()
    
    # Use signup to create a proper user with hashed password
    client = app.test_client()
    
    # First, get the signup page to extract CSRF token
    r = client.get('/signup')
    print('Signup page status:', r.status_code)
    
    # Extract CSRF token from the form
    import re
    match = re.search(r'name="csrf_token" value="([^"]+)"', r.text)
    csrf_token = match.group(1) if match else None
    print('CSRF token:', csrf_token)
    
    # Submit signup
    if csrf_token:
        r2 = client.post('/signup', data={
            'email': 'debug3@test.com',
            'password': 'password123',
            'business_name': 'Debug Business',
            'csrf_token': csrf_token
        }, follow_redirects=True)
        print('Signup redirect status:', r2.status_code)
        print('Final URL:', r2.location)
    else:
        # Try without CSRF (maybe it's not enforced)
        r2 = client.post('/signup', data={
            'email': 'debug3@test.com',
            'password': 'password123',
            'business_name': 'Debug Business'
        }, follow_redirects=True)
        print('Signup redirect status (no CSRF):', r2.status_code)
        print('Final URL:', r2.location)
    
    # Now try to log in
    r3 = client.post('/login', data={'email': 'debug3@test.com', 'password': 'password123'}, follow_redirects=False)
    print('Login status:', r3.status_code, 'Location:', r3.location)
    
    # Dashboard
    r4 = client.get('/', follow_redirects=False)
    print('Dashboard status (no follow):', r4.status_code, 'Location:', r4.location)
    
    if r4.status_code in (302, 303, 307, 308):
        r5 = client.get(r4.location, follow_redirects=True)
        print('Dashboard after redirect - status:', r5.status_code, 'data length:', len(r5.data) if r5.data else 0)
    
    # Invoices
    r6 = client.get('/invoices', follow_redirects=False)
    print('Invoices status (no follow):', r6.status_code, 'Location:', r6.location)
    
    if r6.status_code in (302, 303, 307, 308):
        r7 = client.get(r6.location, follow_redirects=True)
        print('Invoices after redirect - status:', r7.status_code, 'data length:', len(r7.data) if r7.data else 0)