from flask import Blueprint, render_template, redirect, url_for, flash, request, g
from flask_login import login_required
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from app.extensions import db
from app.models import Invoice, InvoiceLineItem, Contact, Business
from app.utils import scoped

invoices_bp = Blueprint("invoices", __name__, url_prefix="/invoices")


def _generate_invoice_number():
    """Atomically claim the next invoice number for the current business."""
    business = Business.query.filter_by(id=g.business_id).with_for_update().first()
    number = business.next_invoice_number
    business.next_invoice_number = number + 1
    return f"INV-{number:04d}"


@invoices_bp.route("/")
@login_required
def list():
    status_filter = request.args.get("status")
    query = scoped(Invoice)
    if status_filter:
        query = query.filter(Invoice.status == status_filter)
    invoices = query.order_by(Invoice.issue_date.desc()).all()
    return render_template("invoices/list.html", invoices=invoices, status_filter=status_filter or "")


@invoices_bp.route("/new", methods=["GET", "POST"])
@login_required
def new():
    customers = scoped(Contact).filter_by(type="customer").order_by(Contact.name).all()

    if request.method == "POST":
        error = None
        customer_id = request.form.get("customer_id")
        if not customer_id:
            error = "Select a customer."

        issue_date_str = request.form.get("issue_date", "").strip()
        try:
            issue_date = datetime.strptime(issue_date_str, "%Y-%m-%d").date()
        except ValueError:
            error = "Enter a valid issue date."
            issue_date = None

        due_date_str = request.form.get("due_date", "").strip()
        due_date = None
        if due_date_str:
            try:
                due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()
            except ValueError:
                error = "Enter a valid due date."

        descriptions = request.form.getlist("line_description[]")
        quantities = request.form.getlist("line_quantity[]")
        unit_prices = request.form.getlist("line_unit_price[]")

        line_items_data = []
        subtotal = Decimal("0.00")
        for desc, qty, price in zip(descriptions, quantities, unit_prices):
            desc = desc.strip()
            if not desc:
                continue
            try:
                qty_dec = Decimal(qty)
                price_dec = Decimal(price)
            except InvalidOperation:
                error = "Enter valid numbers for quantity and price on every line."
                break
            line_total = qty_dec * price_dec
            subtotal += line_total
            line_items_data.append((desc, qty_dec, price_dec, line_total))

        if not line_items_data and not error:
            error = "Add at least one line item."

        if error:
            flash(error, "error")
            return render_template("invoices/form.html", invoice=None, customers=customers, today=date.today().isoformat())

        tax_rate = Decimal("0")
        business = Business.query.filter_by(id=g.business_id).first()
        tax_rate = business.tax_rate or Decimal("0")
        tax_amount = (subtotal * tax_rate / Decimal("100")).quantize(Decimal("0.01"))
        total = subtotal + tax_amount

        invoice = Invoice(
            business_id=g.business_id,
            invoice_number=_generate_invoice_number(),
            customer_id=customer_id,
            issue_date=issue_date,
            due_date=due_date,
            status="draft",
            notes=request.form.get("notes", "").strip() or None,
            subtotal=subtotal,
            tax_amount=tax_amount,
            total=total,
        )
        db.session.add(invoice)
        db.session.flush()

        for desc, qty, price, line_total in line_items_data:
            db.session.add(InvoiceLineItem(
                invoice_id=invoice.id,
                description=desc,
                quantity=qty,
                unit_price=price,
                line_total=line_total,
            ))

        db.session.commit()
        flash(f"Invoice {invoice.invoice_number} created.", "success")
        return redirect(url_for("invoices.view", invoice_id=invoice.id))

    return render_template("invoices/form.html", invoice=None, customers=customers, today=date.today().isoformat())


@invoices_bp.route("/<int:invoice_id>")
@login_required
def view(invoice_id):
    invoice = scoped(Invoice).filter_by(id=invoice_id).first_or_404()
    return render_template("invoices/view.html", invoice=invoice)


@invoices_bp.route("/<int:invoice_id>/mark-paid", methods=["POST"])
@login_required
def mark_paid(invoice_id):
    invoice = scoped(Invoice).filter_by(id=invoice_id).first_or_404()
    invoice.status = "paid"
    db.session.commit()
    flash("Invoice marked as paid.", "success")
    return redirect(url_for("invoices.view", invoice_id=invoice.id))


@invoices_bp.route("/<int:invoice_id>/mark-sent", methods=["POST"])
@login_required
def mark_sent(invoice_id):
    invoice = scoped(Invoice).filter_by(id=invoice_id).first_or_404()
    invoice.status = "sent"
    db.session.commit()
    flash("Invoice marked as sent.", "success")
    return redirect(url_for("invoices.view", invoice_id=invoice.id))


@invoices_bp.route("/<int:invoice_id>/delete", methods=["POST"])
@login_required
def delete(invoice_id):
    invoice = scoped(Invoice).filter_by(id=invoice_id).first_or_404()
    db.session.delete(invoice)
    db.session.commit()
    flash("Invoice deleted.", "success")
    return redirect(url_for("invoices.list"))
