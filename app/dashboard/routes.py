from flask import Blueprint, render_template
from flask_login import login_required
from datetime import date, timedelta
from decimal import Decimal
from calendar import monthrange
from app.models import Invoice, Expense
from app.utils import scoped
import json

dashboard_bp = Blueprint("dashboard", __name__)

@dashboard_bp.route("/")
@login_required
def index():
    today = date.today()
    month_start = today.replace(day=1)

    # This month's paid income
    paid_this_month = scoped(Invoice).filter(
        Invoice.status == "paid",
        Invoice.issue_date >= month_start,
        Invoice.issue_date <= today,
    ).all()
    income_this_month = sum((inv.total for inv in paid_this_month), Decimal("0.00"))

    # This month's expenses
    expenses_this_month = scoped(Expense).filter(
        Expense.date >= month_start,
        Expense.date <= today,
    ).all()
    expenses_total_this_month = sum((e.amount for e in expenses_this_month), Decimal("0.00"))

    net_profit = income_this_month - expenses_total_this_month

    # Unpaid invoices
    unpaid_invoices = scoped(Invoice).filter(
        Invoice.status.in_(["draft", "sent", "overdue"])
    ).order_by(Invoice.due_date.asc().nullslast()).all()
    unpaid_total = sum((inv.total for inv in unpaid_invoices), Decimal("0.00"))

    # Last 6 months of income vs expenses for the chart
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

        m_income = scoped(Invoice).filter(
            Invoice.status == "paid",
            Invoice.issue_date >= m_start,
            Invoice.issue_date <= m_end,
        ).all()
        m_expenses = scoped(Expense).filter(
            Expense.date >= m_start,
            Expense.date <= m_end,
        ).all()

        chart_labels.append(m_start.strftime("%b"))
        chart_income.append(float(sum((inv.total for inv in m_income), Decimal("0.00"))))
        chart_expenses.append(float(sum((e.amount for e in m_expenses), Decimal("0.00"))))

    return render_template(
        "dashboard.html",
        income_this_month=income_this_month,
        expenses_total_this_month=expenses_total_this_month,
        net_profit=net_profit,
        unpaid_invoices=unpaid_invoices[:5],
        unpaid_count=len(unpaid_invoices),
        unpaid_total=unpaid_total,
        chart_labels=json.dumps(chart_labels),
        chart_income=json.dumps(chart_income),
        chart_expenses=json.dumps(chart_expenses),
    )
