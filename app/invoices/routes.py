from flask import Blueprint, render_template, redirect, url_for, flash, request, g, Response
from flask_login import login_required
import csv
from io import BytesIO, StringIO
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from datetime import datetime, date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from xml.sax.saxutils import escape as xml_escape
from app.extensions import db
from app.models import Invoice, InvoiceLineItem, Contact, Business
from app.utils import scoped

invoices_bp = Blueprint("invoices", __name__, url_prefix="/invoices")

CENT = Decimal("0.01")


def _money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def _esc(value) -> str:
    return xml_escape(str(value or ""))


def _generate_invoice_number():
    """Atomically claim the next invoice number for the current business."""
    business = Business.query.filter_by(id=g.business_id).with_for_update().first()
    number = business.next_invoice_number
    business.next_invoice_number = number + 1
    return f"INV-{number:04d}"


@invoices_bp.route("/export/csv")
@login_required
def export_csv():
    def generate():
        yield "Invoice Number,Customer,Date,Status,Total\n"
        # Use a stream-like query to avoid loading all into memory
        query = scoped(Invoice).order_by(Invoice.issue_date.desc())
        for inv in query.yield_per(100):
            yield f"{inv.invoice_number},{inv.customer.name},{inv.issue_date.strftime('%Y-%m-%d')},{inv.status},{inv.total:.2f}\n"
    
    return Response(
        generate(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=invoices_export.csv"}
    )


@invoices_bp.route("/")
@login_required
def list():
    status_filter = request.args.get("status")
    query = scoped(Invoice)
    if status_filter:
        if status_filter not in ("draft", "sent", "paid", "overdue"):
            status_filter = None
        else:
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
        customer = None
        if not customer_id:
            error = "Select a customer."
        else:
            try:
                customer_id_int = int(customer_id)
            except (TypeError, ValueError):
                error = "Select a valid customer."
                customer = None
            else:
                customer = scoped(Contact).filter_by(id=customer_id_int, type="customer").first()
                if customer is None:
                    error = "Select a valid customer."

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
            if qty_dec <= 0 or price_dec < 0:
                error = "Quantity must be above zero and price cannot be negative."
                break
            line_total = _money(qty_dec * price_dec)
            subtotal += line_total
            line_items_data.append((desc, qty_dec, price_dec, line_total))

        if not line_items_data and not error:
            error = "Add at least one line item."

        if due_date and issue_date and due_date < issue_date and not error:
            error = "Due date cannot be before issue date."

        if error:
            flash(error, "error")
            return render_template("invoices/form.html", invoice=None, customers=customers, today=date.today().isoformat())

        tax_rate = Decimal("0")
        business = Business.query.filter_by(id=g.business_id).first()
        tax_rate = business.tax_rate or Decimal("0")
        subtotal = _money(subtotal)
        tax_amount = _money(subtotal * tax_rate / Decimal("100"))
        total = _money(subtotal + tax_amount)

        invoice = Invoice(
            business_id=g.business_id,
            invoice_number=_generate_invoice_number(),
            customer_id=customer.id,
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


@invoices_bp.route("/<int:invoice_id>/pdf")
@login_required
def download_pdf(invoice_id):
    invoice = scoped(Invoice).filter_by(id=invoice_id).first_or_404()

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=20*mm, bottomMargin=20*mm, leftMargin=20*mm, rightMargin=20*mm)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle("InvoiceTitle", parent=styles["Heading1"], fontSize=24, textColor=colors.HexColor("#444444"))
    business_style = ParagraphStyle("BusinessName", parent=styles["Heading2"], fontSize=16)
    normal = styles["Normal"]
    small_grey = ParagraphStyle("SmallGrey", parent=styles["Normal"], fontSize=9, textColor=colors.HexColor("#666666"))

    elements = []

    header_data = [[
        Paragraph(_esc(invoice.business.name), business_style),
        Paragraph(f"<b>INVOICE</b><br/>{_esc(invoice.invoice_number)}", title_style),
    ]]
    header_table = Table(header_data, colWidths=[280, 200])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 20*mm))

    customer_lines = f"<b>Bill To:</b><br/>{_esc(invoice.customer.name)}"
    if invoice.customer.email:
        customer_lines += f"<br/>{_esc(invoice.customer.email)}"
    if invoice.customer.phone:
        customer_lines += f"<br/>{_esc(invoice.customer.phone)}"

    meta_lines = f"Issue Date: {_esc(invoice.issue_date.strftime('%d %b %Y'))}<br/>"
    if invoice.due_date:
        meta_lines += f"Due Date: {_esc(invoice.due_date.strftime('%d %b %Y'))}<br/>"
    meta_lines += f"Status: {_esc(invoice.status.upper())}"

    meta_data = [[Paragraph(customer_lines, normal), Paragraph(meta_lines, normal)]]
    meta_table = Table(meta_data, colWidths=[280, 200])
    meta_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    elements.append(meta_table)
    elements.append(Spacer(1, 15*mm))

    line_data = [["Description", "Qty", "Unit Price", "Total"]]
    currency = invoice.business.currency
    for item in invoice.line_items:
        line_data.append([
            Paragraph(_esc(item.description), normal),
            str(item.quantity),
            f"{currency} {item.unit_price:.2f}",
            f"{currency} {item.line_total:.2f}",
        ])

    items_table = Table(line_data, colWidths=[240, 60, 90, 90])
    items_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#666666")),
        ("LINEBELOW", (0, 0), (-1, 0), 1.2, colors.HexColor("#333333")),
        ("LINEBELOW", (0, 1), (-1, -1), 0.5, colors.HexColor("#eeeeee")),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(items_table)
    elements.append(Spacer(1, 10*mm))

    totals_data = [
        ["Subtotal", f"{currency} {invoice.subtotal:.2f}"],
        ["Tax", f"{currency} {invoice.tax_amount:.2f}"],
        ["Total", f"{currency} {invoice.total:.2f}"],
    ]
    totals_table = Table(totals_data, colWidths=[100, 100], hAlign="RIGHT")
    totals_table.setStyle(TableStyle([
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("FONTNAME", (0, 2), (-1, 2), "Helvetica-Bold"),
        ("FONTSIZE", (0, 2), (-1, 2), 12),
        ("LINEABOVE", (0, 2), (-1, 2), 1.2, colors.HexColor("#333333")),
        ("TOPPADDING", (0, 2), (-1, 2), 8),
    ]))
    elements.append(totals_table)

    if invoice.notes:
        elements.append(Spacer(1, 15*mm))
        elements.append(Paragraph(_esc(invoice.notes), small_grey))

    doc.build(elements)
    buffer.seek(0)

    return Response(
        buffer.read(),
        mimetype="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=invoice-{invoice.invoice_number}.pdf"}
    )


@invoices_bp.route("/<int:invoice_id>/mark-paid", methods=["POST"])
@login_required
def mark_paid(invoice_id):
    invoice = scoped(Invoice).filter_by(id=invoice_id).first_or_404()
    if invoice.status == "paid":
        flash("Invoice is already paid.", "error")
        return redirect(url_for("invoices.view", invoice_id=invoice.id))
    if invoice.status not in ("draft", "sent", "overdue"):
        flash("Only draft, sent or overdue invoices can be marked as paid.", "error")
        return redirect(url_for("invoices.view", invoice_id=invoice.id))
    invoice.status = "paid"
    db.session.commit()
    flash("Invoice marked as paid.", "success")
    return redirect(url_for("invoices.view", invoice_id=invoice.id))


@invoices_bp.route("/<int:invoice_id>/mark-sent", methods=["POST"])
@login_required
def mark_sent(invoice_id):
    invoice = scoped(Invoice).filter_by(id=invoice_id).first_or_404()
    if invoice.status != "draft":
        flash("Only draft invoices can be marked as sent.", "error")
        return redirect(url_for("invoices.view", invoice_id=invoice.id))
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


@invoices_bp.route("/export/pdf_all")
@login_required
def export_pdf_all():
    """Export all paid invoices as a single PDF bundle."""
    invoices = scoped(Invoice).filter_by(status="paid").order_by(Invoice.issue_date.desc()).all()
    if not invoices:
        flash("No paid invoices found to export.", "error")
        return redirect(url_for("invoices.list"))

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=20*mm, bottomMargin=20*mm, leftMargin=20*mm, rightMargin=20*mm)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle("InvoiceTitle", parent=styles["Heading1"], fontSize=24, textColor=colors.HexColor("#444444"))
    business_style = ParagraphStyle("BusinessName", parent=styles["Heading2"], fontSize=16)
    normal = styles["Normal"]
    small_grey = ParagraphStyle("SmallGrey", parent=styles["Normal"], fontSize=9, textColor=colors.HexColor("#666666"))
    
    elements = []
    
    for invoice in invoices:
        # Header
        header_data = [[
            Paragraph(_esc(invoice.business.name), business_style),
            Paragraph(f"<b>INVOICE</b><br/>{_esc(invoice.invoice_number)}", title_style),
        ]]
        header_table = Table(header_data, colWidths=[280, 200])
        header_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 10*mm))

        # Meta
        customer_lines = f"<b>Bill To:</b><br/>{_esc(invoice.customer.name)}"
        if invoice.customer.email:
            customer_lines += f"<br/>{_esc(invoice.customer.email)}"
        if invoice.customer.phone:
            customer_lines += f"<br/>{_esc(invoice.customer.phone)}"

        meta_lines = f"Issue Date: {_esc(invoice.issue_date.strftime('%d %b %Y'))}<br/>"
        if invoice.due_date:
            meta_lines += f"Due Date: {_esc(invoice.due_date.strftime('%d %b %Y'))}<br/>"
        meta_lines += f"Status: {_esc(invoice.status.upper())}"

        meta_data = [[Paragraph(customer_lines, normal), Paragraph(meta_lines, normal)]]
        meta_table = Table(meta_data, colWidths=[280, 200])
        meta_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
        elements.append(meta_table)
        elements.append(Spacer(1, 10*mm))

        # Items
        line_data = [["Description", "Qty", "Unit Price", "Total"]]
        currency = invoice.business.currency
        for item in invoice.line_items:
            line_data.append([
                Paragraph(_esc(item.description), normal),
                str(item.quantity),
                f"{currency} {item.unit_price:.2f}",
                f"{currency} {item.line_total:.2f}",
            ])

        items_table = Table(line_data, colWidths=[240, 60, 90, 90])
        items_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#666666")),
            ("LINEBELOW", (0, 0), (-1, 0), 1.2, colors.HexColor("#333333")),
            ("LINEBELOW", (0, 1), (-1, -1), 0.5, colors.HexColor("#eeeeee")),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        elements.append(items_table)
        elements.append(Spacer(1, 5*mm))

        # Totals
        totals_data = [
            ["Subtotal", f"{currency} {invoice.subtotal:.2f}"],
            ["Tax", f"{currency} {invoice.tax_amount:.2f}"],
            ["Total", f"{currency} {invoice.total:.2f}"],
        ]
        totals_table = Table(totals_data, colWidths=[100, 100], hAlign="RIGHT")
        totals_table.setStyle(TableStyle([
            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ("FONTNAME", (0, 2), (-1, 2), "Helvetica-Bold"),
            ("FONTSIZE", (0, 2), (-1, 2), 12),
            ("LINEABOVE", (0, 2), (-1, 2), 1.2, colors.HexColor("#333333")),
            ("TOPPADDING", (0, 2), (-1, 2), 8),
        ]))
        elements.append(totals_table)
        
        if invoice.notes:
            elements.append(Spacer(1, 5*mm))
            elements.append(Paragraph(_esc(invoice.notes), small_grey))

        # Use a proper PageBreak for professional bundling
        elements.append(PageBreak())

    doc.build(elements)
    buffer.seek(0)

    return Response(
        buffer.read(),
        mimetype="application/pdf",
        headers={"Content-Disposition": "attachment; filename=paid_invoices_bundle.pdf"}
    )
