#!/usr/bin/env python
import os
if os.path.exists('instance/app.db'):
    os.remove('instance/app.db')
    
from datetime import date
from app import create_app
from app.models import db, Invoice, User, Business, Contact
import uuid

app = create_app()
with app.app_context():
    db.create_all()
    
    # Create a user
    user = User(email='test@test.com', password_hash='hash')
    db.session.add(user)
    db.session.commit()
    
    # Create a business
    business = Business(owner_id=user.id, name='Test Business')
    db.session.add(business)
    db.session.commit()
    
    # Create a contact (customer)
    contact = Contact(name='Customer One', email='customer@test.com', type='customer', business_id=user.id)
    db.session.add(contact)
    db.session.commit()
    
    # Create invoices with public_tokens using proper date objects and customer
    for i in range(3):
        inv = Invoice(
            business_id=business.id,
            invoice_number=f'INV-{i+1:04d}',
            customer_id=contact.id,
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
        print(f'  Invoice {inv.id}: customer={inv.customer.name if inv.customer else None}, token={inv.public_token}')
    
    # Check for NULLs
    null_count = Invoice.query.filter(Invoice.public_token.is_(None)).count()
    print(f'NULL tokens: {null_count}')