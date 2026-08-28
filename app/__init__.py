import os
from flask import Flask
from app.extensions import db, login_manager, migrate

def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)

    login_manager.login_view = "auth.login"

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from flask import g
    from flask_login import current_user

    @app.before_request
    def load_current_business():
        if current_user.is_authenticated:
            g.business_id = current_user.business.id

    from app.auth.routes import auth_bp
    app.register_blueprint(auth_bp)

    from app.dashboard.routes import dashboard_bp
    app.register_blueprint(dashboard_bp)

    from app.contacts.routes import contacts_bp
    app.register_blueprint(contacts_bp)

    from app.expenses.routes import expenses_bp
    app.register_blueprint(expenses_bp)

    return app
