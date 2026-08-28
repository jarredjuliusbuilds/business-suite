from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db
from app.models import User, Business, seed_default_expense_categories

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        business_name = request.form.get("business_name", "").strip()

        if not email or not password or not business_name:
            flash("All fields are required.", "error")
            return render_template("auth/signup.html")

        if User.query.filter_by(email=email).first():
            flash("An account with that email already exists.", "error")
            return render_template("auth/signup.html")

        user = User(email=email, password_hash=generate_password_hash(password))
        db.session.add(user)
        db.session.flush()  # gets user.id before commit

        business = Business(owner_id=user.id, name=business_name)
        db.session.add(business)
        db.session.flush()  # gets business.id before commit

        seed_default_expense_categories(business.id)

        db.session.commit()

        login_user(user)
        flash("Welcome! Your account is set up.", "success")
        return redirect(url_for("dashboard.index"))

    return render_template("auth/signup.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for("dashboard.index"))

        flash("Invalid email or password.", "error")

    return render_template("auth/login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
