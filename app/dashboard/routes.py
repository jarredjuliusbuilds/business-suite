from flask import Blueprint, render_template, g
from flask_login import login_required
from datetime import date, timedelta
from decimal import Decimal
from calendar import monthrange
from sqlalchemy import func
from app.extensions import db
from app.models import Invoice, Expense
from app.utils import scoped
import json

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/legal")
def legal():
    return render_template("legal.html")


def _sum_total(query, column):
    value = query.with_entities(func.coalesce(func.sum(column), 0)).scalar()
    return Decimal(str(value)) if value is not None else Decimal("0.00")

@dashboard_bp.route("/")
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
