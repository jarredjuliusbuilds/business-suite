import os
from flask import Flask
from app.extensions import db, login_manager, migrate, csrf

def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    login_manager.login_view = "auth.login"

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from flask import g
    from flask_login import current_user

    @app.before_request
    def load_current_business():
        g.business = None
        if current_user.is_authenticated:
            business = current_user.business
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
