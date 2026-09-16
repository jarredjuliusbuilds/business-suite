#!/usr/bin/env python
import sys
sys.stdout.write('checking null tokens...\n')
from app import create_app
app = create_app()
with app.app_context():
    import sqlite3
    conn = sqlite3.connect('instance/app.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, public_token FROM invoices WHERE public_token IS NULL')
    null_rows = cursor.fetchall()
    sys.stdout.write('Null rows: ' + str(null_rows) + '\n')
    cursor.execute('SELECT COUNT(*) FROM invoices')
    total = cursor.fetchone()[0]
    sys.stdout.write('Total invoices: ' + str(total) + '\n')
    conn.close()
sys.stdout.flush()