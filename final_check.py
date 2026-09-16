from app import create_app
from app.models import Invoice
import sqlite3

app = create_app()
with app.app_context():
    conn = sqlite3.connect('instance/app.db')
    cursor = conn.cursor()
    cursor.execute('PRAGMA table_info(invoices)')
    columns = [row[1] for row in cursor.fetchall()]
    has_public_token = 'public_token' in columns
    print('public_token column exists:', has_public_token)
    
    if has_public_token:
        cursor.execute('SELECT COUNT(*) FROM invoices')
        count = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM invoices WHERE public_token IS NOT NULL')
        filled = cursor.fetchone()[0]
        print('Total invoices:', count)
        print('Invoices with token:', filled)
    
    # Verify routes are registered
    print('Routes with public:')
    for rule in app.url_map.iter_rules():
        if 'public' in rule.rule:
            print('  ', rule.rule, '->', rule.endpoint)
    
conn.close()