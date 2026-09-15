from dotenv import load_dotenv
load_dotenv()
from app import create_app
from app.extensions import db
from werkzeug.security import generate_password_hash
app = create_app()
with app.app_context():
    from app.models import User
    u = User.query.get(1)
    print(f"user: {u.email}", flush=True)
    u.password_hash = generate_password_hash("TestPass123!")
    db.session.commit()
    print("password reset to TestPass123! for user 1", flush=True)
