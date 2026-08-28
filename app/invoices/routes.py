from flask import Blueprint, render_template, redirect, url_for, flash, request, g
from flask_login import login_required, current_user
from decimal import Decimal, InvalidOperation
import datetime

from app.extensions import db
from app.models import Invoice, InvoiceLineItem, Contact, Business
from app.utils import scoped

invoices_bp = Blueprint('invoices', __name__, url_prefix='/invoices')


def get_next_invoice_number(business_id):
    """Return the next sequential invoice number for the business as INV-XXXX."""
    business = Business.query.get(business_id)
    next_num = business.next_invoice_number
    return f"INV-{next_num:04d}"


def increment_invoice_number(business_id):
    """Increment the business's next_invoice_number counter."""
    business = Business.query.get(business_id)
    business.next_invoice_number += 1
    db.session.add(business)


def calculate_totals(items, tax_rate_decimal):
    """Given a list of dicts with quantity and unit_price, calculate subtotal, tax, total."""
    subtotal = Decimal('0.00')
    for item in items:
        qty = Decimal(str(item['quantity']))
        price = Decimal(str(item['unit_price']))
        line_total = qty * price
        item['line_total'] = line_total
        subtotal += line_total
    tax_amount = subtotal * (tax_rate_decimal / Decimal('100'))
    total = subtotal + tax_amount
    return subtotal, tax_amount, total


@invoices_bp.route('/')
@login_required
def list_invoices():
    invoices = scoped(Invoice).order_by(Invoice.created_at.desc()).all()
    return render_template('invoices/list.html', invoices=invoices)


@invoices_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new_invoice():
    if request.method == 'GET':
        customers = scoped(Contact).filter(Contact.type == 'customer').order_by(Contact.name).all()
        return render_template('invoices/form.html', invoice=None, customers=customers)

    # POST: create invoice
    customer_id = request.form.get('customer_id', type=int)
    issue_date_str = request.form.get('issue_date')
    due_date_str = request.form.get('due_date')
    notes = request.form.get('notes', '').strip()
    status = request.form.get('status', 'draft')
    if status not in ('draft', 'sent', 'paid'):
        status = 'draft'

    # Validate customer
    if not customer_id:
        flash('Please select a customer.', 'error')
        return redirect(url_for('invoices.new_invoice'))

    customer = scoped(Contact).filter(Contact.id == customer_id, Contact.type == 'customer').first()
    if not customer:
        flash('Invalid customer.', 'error')
        return redirect(url_for('invoices.new_invoice'))

    # Parse dates
    try:
        issue_date = datetime.datetime.strptime(issue_date_str, '%Y-%m-%d').date() if issue_date_str else datetime.date.today()
        due_date = datetime.datetime.strptime(due_date_str, '%Y-%m-%d').date() if due_date_str else None
    except ValueError:
        flash('Invalid date format.', 'error')
        return redirect(url_for('invoices.new_invoice'))

    # Parse line items
    descriptions = request.form.getlist('description')
    quantities = request.form.getlist('quantity')
    unit_prices = request.form.getlist('unit_price')

    items = []
    for desc, qty_str, price_str in zip(descriptions, quantities, unit_prices):
        desc = desc.strip()
        if not desc:
            continue
        try:
            qty = Decimal(qty_str)
            price = Decimal(price_str)
            if qty < 0 or price < 0:
                raise InvalidOperation
        except (InvalidOperation, ValueError):
            flash('Invalid quantity or price for line item.', 'error')
            return redirect(url_for('invoices.new_invoice'))
        items.append({
            'description': desc,
            'quantity': qty,
            'unit_price': price
        })

    if not items:
        flash('At least one line item is required.', 'error')
        return redirect(url_for('invoices.new_invoice'))

    # Get business's tax rate
    business = Business.query.get(g.business_id)
    tax_rate = Decimal(str(business.tax_rate))

    subtotal, tax_amount, total = calculate_totals(items, tax_rate)

    # Generate invoice number and increment counter
    invoice_number = get_next_invoice_number(g.business_id)
    increment_invoice_number(g.business_id)

    invoice = Invoice(
        business_id=g.business_id,
        invoice_number=invoice_number,
        customer_id=customer.id,
        issue_date=issue_date,
        due_date=due_date,
        status=status,
        notes=notes,
        subtotal=subtotal,
        tax_amount=tax_amount,
        total=total
    )
    db.session.add(invoice)
    db.session.flush()  # get invoice.id

    for item in items:
        line = InvoiceLineItem(
            invoice_id=invoice.id,
            description=item['description'],
            quantity=item['quantity'],
            unit_price=item['unit_price'],
            line_total=item['line_total']
        )
        db.session.add(line)

    db.session.commit()
    flash('Invoice created successfully.', 'success')
    return redirect(url_for('invoices.list_invoices'))


@invoices_bp.route('/<int:invoice_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_invoice(invoice_id):
    invoice = scoped(Invoice).filter(Invoice.id == invoice_id).first_or_404()
    if request.method == 'GET':
        customers = scoped(Contact).filter(Contact.type == 'customer').order_by(Contact.name).all()
        return render_template('invoices/form.html', invoice=invoice, customers=customers)

    # POST: update invoice
    customer_id = request.form.get('customer_id', type=int)
    issue_date_str = request.form.get('issue_date')
    due_date_str = request.form.get('due_date')
    notes = request.form.get('notes', '').strip()
    status = request.form.get('status', 'draft')
    if status not in ('draft', 'sent', 'paid'):
        status = 'draft'

    customer = scoped(Contact).filter(Contact.id == customer_id, Contact.type == 'customer').first()
    if not customer:
        flash('Invalid customer.', 'error')
        return redirect(url_for('invoices.edit_invoice', invoice_id=invoice.id))

    try:
        issue_date = datetime.datetime.strptime(issue_date_str, '%Y-%m-%d').date() if issue_date_str else datetime.date.today()
        due_date = datetime.datetime.strptime(due_date_str, '%Y-%m-%d').date() if due_date_str else None
    except ValueError:
        flash('Invalid date format.', 'error')
        return redirect(url_for('invoices.edit_invoice', invoice_id=invoice.id))

    descriptions = request.form.getlist('description')
    quantities = request.form.getlist('quantity')
    unit_prices = request.form.getlist('unit_price')

    items = []
    for desc, qty_str, price_str in zip(descriptions, quantities, unit_prices):
        desc = desc.strip()
        if not desc:
            continue
        try:
            qty = Decimal(qty_str)
            price = Decimal(price_str)
            if qty < 0 or price < 0:
                raise InvalidOperation
        except (InvalidOperation, ValueError):
            flash('Invalid quantity or price for line item.', 'error')
            return redirect(url_for('invoices.edit_invoice', invoice_id=invoice.id))
        items.append({
            'description': desc,
            'quantity': qty,
            'unit_price': price
        })

    if not items:
        flash('At least one line item is required.', 'error')
        return redirect(url_for('invoices.edit_invoice', invoice_id=invoice.id))

    business = Business.query.get(g.business_id)
    tax_rate = Decimal(str(business.tax_rate))

    subtotal, tax_amount, total = calculate_totals(items, tax_rate)

    # Update invoice fields
    invoice.customer_id = customer.id
    invoice.issue_date = issue_date
    invoice.due_date = due_date
    invoice.status = status
    invoice.notes = notes
    invoice.subtotal = subtotal
    invoice.tax_amount = tax_amount
    invoice.total = total

    # Delete existing line items and add new ones
    InvoiceLineItem.query.filter_by(invoice_id=invoice.id).delete()
    for item in items:
        line = InvoiceLineItem(
            invoice_id=invoice.id,
            description=item['description'],
            quantity=item['quantity'],
            unit_price=item['unit_price'],
            line_total=item['line_total']
        )
        db.session.add(line)

    db.session.commit()
    flash('Invoice updated successfully.', 'success')
    return redirect(url_for('invoices.list_invoices'))


@invoices_bp.route('/<int:invoice_id>/delete', methods=['POST'])
@login_required
def delete_invoice(invoice_id):
    invoice = scoped(Invoice).filter(Invoice.id == invoice_id).first_or_404()
    db.session.delete(invoice)
    db.session.commit()
    flash('Invoice deleted.', 'success')
    return redirect(url_for('invoices.list_invoices'))


@invoices_bp.route('/<int:invoice_id>/mark-sent', methods=['POST'])
@login_required
def mark_sent(invoice_id):
    invoice = scoped(Invoice).filter(Invoice.id == invoice_id).first_or_404()
    invoice.status = 'sent'
    db.session.commit()
    flash('Invoice marked as sent.', 'success')
    return redirect(url_for('invoices.list_invoices'))


@invoices_bp.route('/<int:invoice_id>/mark-paid', methods=['POST'])
@login_required
def mark_paid(invoice_id):
    invoice = scoped(Invoice).filter(Invoice.id == invoice_id).first_or_404()
    invoice.status = 'paid'
    db.session.commit()
    flash('Invoice marked as paid.', 'success')
    return redirect(url_for('invoices.list_invoices'))
