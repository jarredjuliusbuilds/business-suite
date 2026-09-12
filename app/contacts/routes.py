from flask import Blueprint, render_template, redirect, url_for, flash, request, g
from flask_login import login_required
from datetime import datetime
import re
from sqlalchemy import func
from app.extensions import db
from app.models import Contact, Invoice, Expense, Task
from app.utils import scoped

contacts_bp = Blueprint("contacts", __name__, url_prefix="/contacts")

VALID_CONTACT_TYPES = ("customer", "supplier")

def _is_valid_email(email):
    if not email: return True
    return bool(re.match(r"[^@]+@[^@]+\.[^@]+", email))

def _clean_contact_type(raw):
    value = (raw or "customer").strip().lower()
    return value if value in VALID_CONTACT_TYPES else "customer"

@contacts_bp.route("/")
@login_required
def list():
    q = request.args.get("q", "").strip()
    query = scoped(Contact)
    if q:
        query = query.filter(
            (Contact.name.ilike(f"%{q}%")) | 
            (Contact.email.ilike(f"%{q}%")) | 
            (Contact.phone.ilike(f"%{q}%"))
        )
    contacts = query.order_by(Contact.name).all()
    return render_template("contacts/list.html", contacts=contacts, q=q)


@contacts_bp.route("/new", methods=["GET", "POST"])
@login_required
def new():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip() or None
        
        if not name:
            flash("Name is required.", "error")
            return render_template("contacts/form.html", contact=None)
        
        if not _is_valid_email(email):
            flash("Enter a valid email address.", "error")
            return render_template("contacts/form.html", contact=None)
            
        contact = Contact(
            business_id=g.business_id,
            type=_clean_contact_type(request.form.get("type")),
            name=name,
            email=email,
            phone=request.form.get("phone", "").strip() or None,
            notes=request.form.get("notes", "").strip() or None,
        )
        db.session.add(contact)
        db.session.commit()
        flash("Contact added.", "success")
        return redirect(url_for("contacts.list"))

    return render_template("contacts/form.html", contact=None)


@contacts_bp.route("/<int:contact_id>")
@login_required
def view(contact_id):
    contact = scoped(Contact).filter_by(id=contact_id).first_or_404()
    
    # Aggregate invoice data for this contact using SQL for performance
    invoices_query = scoped(Invoice).filter_by(customer_id=contact_id)
    
    total_billed = invoices_query.with_entities(func.coalesce(func.sum(Invoice.total), 0)).scalar() or Decimal("0.00")
    total_paid = invoices_query.filter(Invoice.status == 'paid').with_entities(func.coalesce(func.sum(Invoice.total), 0)).scalar() or Decimal("0.00")
    total_outstanding = total_billed - total_paid
    
    invoices = invoices_query.order_by(Invoice.issue_date.desc()).all()
    
    # Related tasks
    tasks = scoped(Task).filter_by(contact_id=contact_id).order_by(Task.due_date.asc().nullslast()).all()
    
    return render_template("contacts/view.html", 
                           contact=contact, 
                           invoices=invoices, 
                           total_billed=total_billed, 
                           total_paid=total_paid, 
                           total_outstanding=total_outstanding, 
                           tasks=tasks)

@contacts_bp.route("/<int:contact_id>/edit", methods=["GET", "POST"])
@login_required
def edit(contact_id):
    contact = scoped(Contact).filter_by(id=contact_id).first_or_404()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip() or None
        
        if not name:
            flash("Name is required.", "error")
            return render_template("contacts/form.html", contact=contact)
        
        if not _is_valid_email(email):
            flash("Enter a valid email address.", "error")
            return render_template("contacts/form.html", contact=contact)
            
        contact.type = _clean_contact_type(request.form.get("type"))
        contact.name = name
        contact.email = email
        contact.phone = request.form.get("phone", "").strip() or None
        contact.notes = request.form.get("notes", "").strip() or None

        db.session.commit()
        flash("Contact updated.", "success")
        return redirect(url_for("contacts.list"))

    return render_template("contacts/form.html", contact=contact)


@contacts_bp.route("/<int:contact_id>/delete", methods=["POST"])
@login_required
def delete(contact_id):
    contact = scoped(Contact).filter_by(id=contact_id).first_or_404()
    has_invoices = scoped(Invoice).filter_by(customer_id=contact_id).first() is not None
    has_expenses = scoped(Expense).filter_by(supplier_id=contact_id).first() is not None
    has_tasks = scoped(Task).filter_by(contact_id=contact_id).first() is not None
    if has_invoices or has_expenses or has_tasks:
        flash("Cannot delete contact with invoices, expenses or tasks. Reassign them first.", "error")
        return redirect(url_for("contacts.list"))
    db.session.delete(contact)
    db.session.commit()
    flash("Contact deleted.", "success")
    return redirect(url_for("contacts.list"))
