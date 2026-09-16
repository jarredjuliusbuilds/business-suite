from app import create_app
from app.models import Invoice
import warnings
warnings.filterwarnings('ignore')

app = create_app()

with app.app_context():
    inv = Invoice.query.first()
    print(f'Testing public view for invoice {inv.id}, token: {inv.public_token}')
    
    client = app.test_client()
    
    # Test public view - no login required
    r = client.get(f'/invoices/public/{inv.public_token}')
    print(f'Public view status: {r.status_code}')
    print(f'Public view data length: {len(r.data) if r.data else 0}')
    if r.data:
        text = r.data.decode('utf-8')[:200]
        print(f'First 200 chars: {text}')
    
    # Test 404 for invalid token
    r2 = client.get('/invoices/public/invalid-token')
    print(f'Invalid token status: {r2.status_code}')
PYEOF