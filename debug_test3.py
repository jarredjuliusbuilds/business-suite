from app import create_app
from app.models import User, Business
from app.extensions import db
from flask_login import LoginManager, login_user, current_user
import warnings
warnings.filterwarnings('ignore')

app = create_app()
app.config['PROPAGATE_EXCEPTIONS'] = True
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test_debug4.db'

with app.app_context():
    db.create_all()
    
    user = User(email='debug4@test.com', password_hash='hash')
    db.session.add(user)
    db.session.commit()
    
    biz = Business(owner_id=user.id, name='Debug Business')
    db.session.add(biz)
    db.session.commit()
    user.business = biz
    db.session.commit()
    
    login_manager = LoginManager()
    login_manager.init_app(app)
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    client = app.test_client()
    
    # Log in
    with client.session_transaction() as sess:
        login_user(user)
    
    # Dashboard
    print('=== DASHBOARD ===')
    r = client.get('/', follow_redirects=False)
    print('Dashboard raw status:', r.status_code)
    print('Dashboard headers:', dict(r.headers))
    if r.location:
        print('Dashboard redirect location:', r.location)
        r2 = client.get(r.location, follow_redirects=True)
        print('Dashboard final status:', r5.status_code if 'r5' in dir() else 'N/A')
        r5 = client.get(r.location, follow_redirects=True)
        print('Dashboard final status:', r5.status_code)
        print('Dashboard data length:', len(r5.data) if r5.data else 0)
        print('Dashboard has error template:', '500' in r5.data.decode('utf-8', errors='replace') if r5.data else False)
    
    # Invoices
    print('\\n=== INVOICES ===')
    r6 = client.get('/invoices', follow_redirects=False)
    print('Invoices raw status:', r6.status_code)
    if r6.location:
        print('Invoices redirect location:', r6.location)
        r7 = client.get(r6.location, follow_redirects=True)
        print('Invoices final status:', r7.status_code)
        print('Invoices data length:', len(r7.data) if r7.data else 0)
        print('Invoices has error template:', '500' in r7.data.decode('utf-8', errors='replace') if r7.data else False)