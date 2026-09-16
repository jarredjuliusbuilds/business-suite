#!/usr/bin/env python
import sys
sys.stdout.write('starting...\n')
from app import create_app
app = create_app()
with app.app_context():
    import sqlite3
    conn = sqlite3.connect('instance/app.db')
    cursor = conn.cursor()
    cursor.execute('PRAGMA table_info(invoices)')
    columns = [row[1] for row in cursor.fetchall()]
    sys.stdout.write('Columns: ' + str(columns) + '\n')
    if 'public_token' in columns:
        cursor.execute('SELECT id, public_token FROM invoices LIMIT 3')
        rows = cursor.fetchall()
        sys.stdout.write('Sample tokens: ' + str(rows) + '\n')
    conn.close()
sys.stdout.flush()