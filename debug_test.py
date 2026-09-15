from app import create_app
from app.models import User, Business
from app.extensions import db
import warnings
warnings.filterwarnings('ignore')

app = create_app()
app.config['PROPAGATE_EXCEPTIONS'] = True
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test_debug2.db'

with app.app_context():
    db.create_all()
    user = User.query.filter_by(email='debug2@test.com').first()
    if not user:
        user = User(email='debug2@test.com', password_hash='hash')
        db.session.add(user)
        db.session.commit()
    
    if not user.business:
        biz = Business(owner_id=user.id, name='Debug Business')
        db.session.add(biz)
        db.session.commit()
        user.business = biz
        db.session.commit()
    
    client = app.test_client()
    
    # Log in
    r = client.post('/login', data={'email': 'debug2@test.com', 'password': 'password123'}, follow_redirects=False)
    print('Login redirect status:', r.status_code, 'Location:', r.location)
    
    # Try dashboard - no follow to see the actual response
    r2 = client.get('/', follow_redirects=False)
    print('Dashboard status:', r2.status_code, 'Location:', r2.location)
    
    # Follow the redirect
    if r2.status_code in (302, 303, 307, 308):
        r3 = client.get(r2.location, follow_redirects=True)
        print('Dashboard after redirect - status:', r3.status_code)
        print('Dashboard data (first 500 chars):', r3.data.decode('utf-8')[:500] if r3.data else 'None')
    
    # Try invoices - no follow
    r4 = client.get('/invoices', follow_redirects=False)
    print('Invoices status:', r4.status_code, 'Location:', r4.location)
    
    if r4.status_code in (302, 303, 307, 308):
        r5 = client.get(r4.location, follow_redirects=True)
        print('Invoices after redirect - status:', r5.status_code)
        print('Invoices data (first 500 chars):', r5.data.decode('utf-8')[:500] if r5.data else 'None')