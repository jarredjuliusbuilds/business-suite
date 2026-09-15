from dotenv import load_dotenv
load_dotenv()
print("loaded env", flush=True)
from app import create_app
print("imported", flush=True)
app = create_app()
print("created", flush=True)
print("PROPAGATE:", app.config.get("PROPAGATE_EXCEPTIONS"), flush=True)
with app.app_context():
    from app.models import User
    u = User.query.first()
    print("first user:", u.id, u.email if u else None, flush=True)
print("done", flush=True)
