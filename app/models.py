from datetime import datetime
from flask_login import UserMixin
from app.extensions import db

class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    business = db.relationship("Business", backref="owner", uselist=False)


class Business(db.Model):
    __tablename__ = "businesses"
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    currency = db.Column(db.String(3), default="ZAR")
    tax_rate = db.Column(db.Numeric(5, 2), default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Contact(db.Model):
    __tablename__ = "contacts"
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey("businesses.id"), nullable=False, index=True)
    type = db.Column(db.String(20), nullable=False, default="customer")  # 'customer' or 'supplier'
    name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255))
    phone = db.Column(db.String(50))
    notes = db.Column(db.Text)
    last_contact = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    business = db.relationship("Business", backref="contacts")


class ExpenseCategory(db.Model):
    __tablename__ = "expense_categories"
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey("businesses.id"), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)

    business = db.relationship("Business", backref="expense_categories")


class Expense(db.Model):
    __tablename__ = "expenses"
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey("businesses.id"), nullable=False, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey("expense_categories.id"), nullable=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey("contacts.id"), nullable=True)
    date = db.Column(db.Date, nullable=False, index=True)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    description = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    business = db.relationship("Business", backref="expenses")
    category = db.relationship("ExpenseCategory", backref="expenses")
    supplier = db.relationship("Contact", backref="expenses")


DEFAULT_EXPENSE_CATEGORIES = [
    "Supplies",
    "Rent",
    "Utilities",
    "Transport",
    "Marketing",
    "Other",
]


def seed_default_expense_categories(business_id):
    for name in DEFAULT_EXPENSE_CATEGORIES:
        db.session.add(ExpenseCategory(business_id=business_id, name=name))
