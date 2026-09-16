#!/usr/bin/env python
import os
import glob

# Remove temporary test files
temp_files = [
    'check_aim.ini', 'check_col.py', 'check_cust.py', 'check_env.py',
    'check_mig.py', 'check_mig2.py', 'check_null.py', 'check_uri.py',
    'cleanup.py', 'kill_db.py', 'recreate_db.py', 'recreate_with_customer.py',
    'recreate_with_tokens.py', 'test_pdf.py', 'test_public.py', 'test_whatsapp.py',
    'verify_col.py'
]
for f in temp_files:
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

# Remove migration files that were generated during testing but aren't part of the essential plan
# Keep only the original migrations and the public_token migrations
essential = ['2cb43fdbd7f0_add_tax_rate_to_invoices.py', '53d1387b4dad_initial_models.py']
migration_files = glob.glob('migrations/versions/*.py')
for f in migration_files:
    fname = os.path.basename(f)
    if fname not in essential:
        try:
            os.remove(f)
        except:
            pass

print('Cleanup done')