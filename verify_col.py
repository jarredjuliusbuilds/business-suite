from app import create_app
from app.models import Invoice
import sqlite3

app = create_app()
with app.app_context():
    conn = sqlite3.connect('instance/app.db')
    cursor = conn.cursor()
    cursor.execute('PRAGMA table_info(invoices)')
    columns = [row[1] for row in cursor.fetchall()]
    print('Columns:', columns)
    if 'public_token' in columns:
        cursor.execute('SELECT id, public_token FROM invoices')
        rows = cursor.fetchall()
        print('Tokens populated:', len(rows), 'invoices')
        for row in rows[:3]:
            print(f'  ID {row[0]}: {row[1]}')
    conn.close()