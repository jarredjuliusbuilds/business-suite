#!/usr/bin/env python
import os
if os.path.exists('instance/app.db'):
    os.remove('instance/app.db')
    
from datetime import date
from app import create_app
from app.models import db, Invoice, User, Business
import uuid

app = create_app()
with app.app_context():
    db.create_all()
    
    # Create a business and user first
    from app.models import User
    user = User(email='test@test.com', password_hash='hash')
    db.session.add(user)
    db.session.commit()
    
    business = Business(owner_id=user.id, name='Test Business')
    db.session.add(business)
    db.session.commit()
    
    # Create invoices with public_tokens using proper date objects
    for i in range(5):
        inv = Invoice(
            business_id=business.id,
            invoice_number=f'INV-{i+1:04d}',
            customer_id=1,
            issue_date=date(2026, 9, 1),
            status='draft'
        )
        inv.public_token = str(uuid.uuid4())
        db.session.add(inv)
    db.session.commit()
    
    # Verify
    all_invoices = Invoice.query.all()
    print(f'Created {len(all_invoices)} invoices')
    for inv in all_invoices:
        print(f'  Invoice {inv.id}: token={inv.public_token}')
    
    # Check for NULLs
    null_count = Invoice.query.filter(Invoice.public_token.is_(None)).count()
    print(f'NULL tokens: {null_count}')