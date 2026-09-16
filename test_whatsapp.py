from app import create_app
from app.models import Invoice
from flask import url_for
from urllib.parse import urlencode
import warnings
warnings.filterwarnings('ignore')

app = create_app()

with app.app_context():
    inv = Invoice.query.first()
    print(f'Testing WhatsApp sharing for invoice {inv.id}')
    
    text = 'Invoice ' + inv.invoice_number + ' from ' + inv.business.name + ' — Total: R' + '%.2f' % inv.total + ' — View: ' + url_for('invoices.public_view', token=inv.public_token, _external=True)
    print(f'WhatsApp text: {text[:80]}...')
    
    # Check urlencode works
    encoded = urlencode({'text': text})
    print(f'Encoded: {encoded[:80]}...')
PYEOF