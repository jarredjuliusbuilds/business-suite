import os
import logging
from flask import Flask, render_template

from app.extensions import db, login_manager, migrate, csrf


def create_app():
    app = Flask(__name__)

    secret_key = os.environ.get("SECRET_KEY")
    if not secret_key:
        logging.getLogger(__name__).warning(
            "SECRET_KEY not set — using secure dev fallback. Set SECRET_KEY in production."
        )
        secret_key = "dev-fallback-key-for-local-development-only"
    app.config["SECRET_KEY"] = secret_key

    database_url = os.environ.get("DATABASE_URL") or "sqlite:///app.db"
    if not os.environ.get("DATABASE_URL"):
        logging.getLogger(__name__).warning(
            "DATABASE_URL not set — falling back to sqlite:///app.db for local dev."
        )
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    login_manager.login_view = "auth.login"

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    from flask import g
    from flask_login import current_user

    @app.before_request
    def load_current_business():
        g.business = None
        g.business_id = None
        if current_user.is_authenticated:
            business = current_user.business
            if business is None:
                return
            g.business_id = business.id
            g.business = business

    from app.auth.routes import auth_bp
    app.register_blueprint(auth_bp)

    from app.dashboard.routes import dashboard_bp
    app.register_blueprint(dashboard_bp)

    from app.contacts.routes import contacts_bp
    app.register_blueprint(contacts_bp)

    from app.expenses.routes import expenses_bp
    app.register_blueprint(expenses_bp)

    from app.invoices.routes import invoices_bp
    app.register_blueprint(invoices_bp)

    from app.tasks.routes import tasks_bp
    app.register_blueprint(tasks_bp)

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template("errors/500.html"), 500

    return app
