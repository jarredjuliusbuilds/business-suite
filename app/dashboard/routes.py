from flask import Blueprint, render_template, g, request, Response
from flask_login import login_required
import datetime
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from calendar import monthrange
from sqlalchemy import func
from app.extensions import db
from app.models import Invoice, Expense
from app.utils import scoped
import json
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from xml.sax.saxutils import escape as xml_escape

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/legal")
def legal():
    return render_template("legal.html")


def _sum_total(query, column):
    value = query.with_entities(func.coalesce(func.sum(column), 0)).scalar()
    return Decimal(str(value)) if value is not None else Decimal("0.00")

def _money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

def _esc(value) -> str:
    return xml_escape(str(value or ""))

def _generate_summary_pdf(start_date, end_date, income, expenses, net_profit):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=20*mm, bottomMargin=20*mm, leftMargin=20*mm, rightMargin=20*mm)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle("Title", parent=styles["Heading1"], fontSize=22, textColor=colors.HexColor("#0F766E"), spaceAfter=20)
    label_style = ParagraphStyle("Label", parent=styles["Normal"], fontSize=12, textColor=colors.HexColor("#64748B"))
    value_style = ParagraphStyle("Value", parent=styles["Normal"], fontSize=14, fontName="Helvetica-Bold")
    
    elements = []
    elements.append(Paragraph("Business Performance Report", title_style))
    elements.append(Paragraph(f"Period: {start_date} to {end_date}", label_style))
    elements.append(Spacer(1, 10*mm))
    
    data = [
        ["Total Income", f"R {income:.2f}"],
        ["Total Expenses", f"R {expenses:.2f}"],
        ["Net Profit", f"R {net_profit:.2f}"]
    ]
    
    t = Table(data, colWidths=[100, 100])
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica"),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica-Bold"),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.grey),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    elements.append(t)
    
    doc.build(elements)
    buffer.seek(0)
    return buffer.read()

@dashboard_bp.route("/reports/pl/pdf")
@login_required
def profit_loss_pdf():
    start_date_str = request.args.get("start")
    end_date_str = request.args.get("end")
    
    today = date.today()
    start_date = date(today.year, 1, 1)
    end_date = today
    
    if start_date_str:
        try: start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        except ValueError: pass
    if end_date_str:
        try: end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        except ValueError: pass
        
    income = _sum_total(scoped(Invoice).filter(Invoice.status == "paid", Invoice.issue_date >= start_date, Invoice.issue_date <= end_date), Invoice.total)
    expenses = _sum_total(scoped(Expense).filter(Expense.date >= start_date, Expense.date <= end_date), Expense.amount)
    net_profit = income - expenses
    
    pdf_content = _generate_summary_pdf(start_date.isoformat(), end_date.isoformat(), income, expenses, net_profit)
    
    return Response(
        pdf_content,
        mimetype="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=profit_loss_{start_date}_{end_date}.pdf"}
    )
@login_required
def index():
    today = date.today()
    month_start = today.replace(day=1)

    # This month's paid income (SQL SUM, no full table load)
    income_this_month = _sum_total(
        scoped(Invoice).filter(
            Invoice.status == "paid",
            Invoice.issue_date >= month_start,
            Invoice.issue_date <= today,
        ),
        Invoice.total,
    )

    # This month's expenses (SQL SUM)
    expenses_total_this_month = _sum_total(
        scoped(Expense).filter(
            Expense.date >= month_start,
            Expense.date <= today,
        ),
        Expense.amount,
    )

    net_profit = income_this_month - expenses_total_this_month

    # Unpaid invoices — DO NOT .all() the whole table: count + total in SQL, top 5 only
    unpaid_base = scoped(Invoice).filter(
        Invoice.status.in_(["draft", "sent", "overdue"])
    )
    unpaid_count = unpaid_base.with_entities(func.count(Invoice.id)).scalar() or 0
    unpaid_total = _sum_total(unpaid_base, Invoice.total)
    unpaid_invoices = unpaid_base.order_by(Invoice.due_date.asc().nullslast()).limit(5).all()

    # Last 6 months of income vs expenses for the chart (SQL SUM per month)
    chart_labels = []
    chart_income = []
    chart_expenses = []

    for i in range(5, -1, -1):
        year = today.year
        month = today.month - i
        while month <= 0:
            month += 12
            year -= 1
        _, last_day = monthrange(year, month)
        m_start = date(year, month, 1)
        m_end = date(year, month, last_day)

        m_income = _sum_total(
            scoped(Invoice).filter(
                Invoice.status == "paid",
                Invoice.issue_date >= m_start,
                Invoice.issue_date <= m_end,
            ),
            Invoice.total,
        )
        m_exp = _sum_total(
            scoped(Expense).filter(
                Expense.date >= m_start,
                Expense.date <= m_end,
            ),
            Expense.amount,
        )

        chart_labels.append(m_start.strftime("%b"))
        chart_income.append(float(m_income))
        chart_expenses.append(float(m_exp))

    return render_template(
        "dashboard.html",
        income_this_month=income_this_month,
        expenses_total_this_month=expenses_total_this_month,
        net_profit=net_profit,
        unpaid_invoices=unpaid_invoices,
        unpaid_count=unpaid_count,
        unpaid_total=unpaid_total,
        chart_labels=json.dumps(chart_labels),
        chart_income=json.dumps(chart_income),
        chart_expenses=json.dumps(chart_expenses),
    )

@dashboard_bp.route("/reports/pl")
@login_required
def profit_loss():
    start_date_str = request.args.get("start")
    end_date_str = request.args.get("end")
    
    today = date.today()
    # Default to current year
    start_date = date(today.year, 1, 1)
    end_date = today
    
    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        except ValueError: pass
    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        except ValueError: pass
        
    income = _sum_total(
        scoped(Invoice).filter(
            Invoice.status == "paid",
            Invoice.issue_date >= start_date,
            Invoice.issue_date <= end_date,
        ),
        Invoice.total,
    )
    
    expenses = _sum_total(
        scoped(Expense).filter(
            Expense.date >= start_date,
            Expense.date <= end_date,
        ),
        Expense.amount,
    )
    
    return render_template(
        "pl.html",
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
        income=income,
        expenses=expenses,
        net_profit=income - expenses,
    )
