#!/usr/bin/env python
import os
if os.path.exists('instance/app.db'):
    os.remove('instance/app.db')
    
from app import create_app
from app.models import db, Invoice
import uuid

app = create_app()
with app.app_context():
    db.create_all()
    
    from app.models import User, Business
    for i in range(3):
        inv = Invoice(
            business_id=1, 
            invoice_number=f'INV-{i+1:04d}',
            customer_id=1,
            issue_date='2026-09-01',
            status='draft'
        )
        inv.public_token = str(uuid.uuid4())
        db.session.add(inv)
    db.session.commit()
    
    all_invoices = Invoice.query.all()
    print(f'Created {len(all_invoices)} invoices')
    for inv in all_invoices:
        print(f'  Invoice {inv.id}: token={inv.public_token}')