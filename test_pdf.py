from app import create_app
from app.models import Invoice
import warnings
warnings.filterwarnings('ignore')

app = create_app()

with app.app_context():
    inv = Invoice.query.first()
    print(f'Testing public download PDF for invoice {inv.id}, token: {inv.public_token}')
    
    client = app.test_client()
    
    # Test public download PDF - no login required
    r = client.get(f'/invoices/public/{inv.id}/pdf/{inv.public_token}')
    print(f'Public download PDF status: {r.status_code}')
    print(f'Public download PDF content type: {r.content_type}')
    print(f'PDF data length: {len(r.data)}')
    if r.data:
        print(f'PDF starts with: {r.data[:20]}')
    
    # Test 404 for invalid token
    r2 = client.get('/invoices/public/999/pdf/invalid')
    print(f'Invalid PDF status: {r2.status_code}')
    
    # Test 404 for wrong token
    r3 = client.get('/invoices/public/999/pdf/token')
    print(f'Wrong token status: {r3.status_code}')