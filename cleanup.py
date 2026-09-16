#!/usr/bin/env python
import os
# Remove temp files
files_to_remove = [
    'check_uri.py', 'check_aim.ini', 'check_env.py', 'check_null.py',
    'recreate_db.py', 'recreate_with_tokens.py', 'kill_db.py',
    'token_update.log', 'a.txt', 'a2.txt', 'test_output.txt',
    'server.log', 'server_trace.log', 'setup.log',
    'debug_test.py', 'debug_test2.py', 'debug_test3.py', 'debug_test4.py', 'debug_test5.py',
    'debug_routes.txt', 'setup.log', 'token_update.log'
]
for f in files_to_remove:
    try:
        path = os.path.join('instance', f)
        if os.path.exists(path):
            os.remove(path)
    except:
        try:
            if os.path.exists(f):
                os.remove(f)
        except:
            pass

# Remove instance db
if os.path.exists('instance/app.db'):
    os.remove('instance/app.db')

print('Cleaned up')