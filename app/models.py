import datetime
from flask_login import UserMixin
from app.extensions import db

class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    business = db.relationship("Business", backref="owner", uselist=False)


class Business(db.Model):
    __tablename__ = "businesses"
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    currency = db.Column(db.String(3), default="ZAR")
    tax_rate = db.Column(db.Numeric(5, 2), default=0)
    next_invoice_number = db.Column(db.Integer, nullable=False, default=1)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)


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
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

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
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

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


class Invoice(db.Model):
    __tablename__ = 'invoices'
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('businesses.id'), nullable=False, index=True)
    invoice_number = db.Column(db.String(20), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('contacts.id'), nullable=False)
    issue_date = db.Column(db.Date, nullable=False, default=datetime.date.today)
    due_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='draft')
    notes = db.Column(db.Text, nullable=True)
    subtotal = db.Column(db.Numeric(10,2), nullable=False, default=0)
    tax_amount = db.Column(db.Numeric(10,2), nullable=False, default=0)
    total = db.Column(db.Numeric(10,2), nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=True, onupdate=datetime.datetime.utcnow)

    business = db.relationship('Business', backref=db.backref('invoices', lazy=True))
    customer = db.relationship('Contact', backref=db.backref('invoices', lazy=True))
    line_items = db.relationship('InvoiceLineItem', backref='invoice', cascade='all, delete-orphan', lazy=True)


class InvoiceLineItem(db.Model):
    __tablename__ = 'invoice_line_items'
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'), nullable=False, index=True)
    description = db.Column(db.String(255), nullable=False)
    quantity = db.Column(db.Numeric(10,2), nullable=False, default=1)
    unit_price = db.Column(db.Numeric(10,2), nullable=False, default=0)
    line_total = db.Column(db.Numeric(10,2), nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
