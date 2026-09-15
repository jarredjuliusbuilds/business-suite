from dotenv import load_dotenv
load_dotenv()
import traceback
from app import create_app
app = create_app()
print("PROPAGATE:", app.config.get("PROPAGATE_EXCEPTIONS"), flush=True)
c = app.test_client()
# login as user 1 via session
with c.session_transaction() as s:
    s['_user_id'] = '1'
    s['_fresh'] = True
print("session set for user 1", flush=True)

for path in ["/", "/invoices/"]:
    print(f"\n===== GET {path} =====", flush=True)
    try:
        r = c.get(path)
        print(f"STATUS: {r.status_code}", flush=True)
        # print first 3000 chars of body for context
        try:
            txt = r.data.decode('utf-8', errors='ignore')
            print(f"BODY snippet (first 2000 chars):\n{txt[:2000]}", flush=True)
        except Exception as e:
            print(f"body decode error: {e}", flush=True)
    except Exception:
        print(f"EXCEPTION on GET {path}:", flush=True)
        traceback.print_exc()
    print(f"===== END {path} =====\n", flush=True)
