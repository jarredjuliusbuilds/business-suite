#!/usr/bin/env python
import sys
sys.stdout.write('checking migration...\n')
from app import create_app
app = create_app()
with app.app_context():
    import sqlite3
    conn = sqlite3.connect('instance/app.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM alembic_version')
    version = cursor.fetchone()
    sys.stdout.write('alembic_version: ' + str(version) + '\n')
    conn.close()
sys.stdout.flush()