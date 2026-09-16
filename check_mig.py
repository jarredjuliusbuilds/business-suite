#!/usr/bin/env python
import sys
sys.stdout.write('checking migration status...\n')
from app import create_app
app = create_app()
with app.app_context():
    from alembic.command import get_head
    from alembic.config import Config
    cfg = Config('migrations/alembic.ini')
    head = get_head(cfg)
    sys.stdout.write('Head: ' + str(head) + '\n')
    
    from alembic.command import get_current_head
    curr = get_current_head(cfg)
    sys.stdout.write('Current: ' + str(curr) + '\n')
sys.stdout.flush()