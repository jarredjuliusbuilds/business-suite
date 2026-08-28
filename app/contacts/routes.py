from flask import Blueprint, render_template, redirect, url_for, flash, request, g
from flask_login import login_required
from datetime import datetime
from app.extensions import db
from app.models import Contact
from app.utils import scoped

contacts_bp = Blueprint("contacts", __name__, url_prefix="/contacts")

@contacts_bp.route("/")
@login_required
def list():
    contacts = scoped(Contact).order_by(Contact.name).all()
    return render_template("contacts/list.html", contacts=contacts)


@contacts_bp.route("/new", methods=["GET", "POST"])
@login_required
def new():
    if request.method == "POST":
        contact = Contact(
            business_id=g.business_id,
            type=request.form.get("type", "customer"),
            name=request.form.get("name", "").strip(),
            email=request.form.get("email", "").strip() or None,
            phone=request.form.get("phone", "").strip() or None,
            notes=request.form.get("notes", "").strip() or None,
        )
        if not contact.name:
            flash("Name is required.", "error")
            return render_template("contacts/form.html", contact=None)

        db.session.add(contact)
        db.session.commit()
        flash("Contact added.", "success")
        return redirect(url_for("contacts.list"))

    return render_template("contacts/form.html", contact=None)


@contacts_bp.route("/<int:contact_id>/edit", methods=["GET", "POST"])
@login_required
def edit(contact_id):
    contact = scoped(Contact).filter_by(id=contact_id).first_or_404()

    if request.method == "POST":
        contact.type = request.form.get("type", "customer")
        contact.name = request.form.get("name", "").strip()
        contact.email = request.form.get("email", "").strip() or None
        contact.phone = request.form.get("phone", "").strip() or None
        contact.notes = request.form.get("notes", "").strip() or None

        if not contact.name:
            flash("Name is required.", "error")
            return render_template("contacts/form.html", contact=contact)

        db.session.commit()
        flash("Contact updated.", "success")
        return redirect(url_for("contacts.list"))

    return render_template("contacts/form.html", contact=contact)


@contacts_bp.route("/<int:contact_id>/delete", methods=["POST"])
@login_required
def delete(contact_id):
    contact = scoped(Contact).filter_by(id=contact_id).first_or_404()
    db.session.delete(contact)
    db.session.commit()
    flash("Contact deleted.", "success")
    return redirect(url_for("contacts.list"))
