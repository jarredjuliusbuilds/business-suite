from flask import Blueprint, render_template, redirect, url_for, flash, request, g
from flask_login import login_required
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from sqlalchemy import func
from app.extensions import db
from app.models import Expense, ExpenseCategory, Contact
from app.utils import scoped

expenses_bp = Blueprint("expenses", __name__, url_prefix="/expenses")


def _validate_expense_refs(category_id_raw, supplier_id_raw):
    """Return (category_id, supplier_id, error). Ensures refs belong to this business."""
    category_id = None
    supplier_id = None
    if category_id_raw:
        try:
            category_id = int(category_id_raw)
        except (TypeError, ValueError):
            return None, None, "Select a valid category."
        if scoped(ExpenseCategory).filter_by(id=category_id).first() is None:
            return None, None, "Select a valid category."
    if supplier_id_raw:
        try:
            supplier_id = int(supplier_id_raw)
        except (TypeError, ValueError):
            return None, None, "Select a valid supplier."
        if scoped(Contact).filter_by(id=supplier_id, type="supplier").first() is None:
            return None, None, "Select a valid supplier."
    return category_id, supplier_id, None


def _parse_amount(raw):
    try:
        amount = Decimal((raw or "0").strip())
    except (InvalidOperation, AttributeError):
        return None, "Enter a valid amount."
    if amount <= 0:
        return None, "Amount must be greater than zero."
    return amount, None


@expenses_bp.route("/summary")
@login_required
def summary():
    # Calculate totals per category using SQL GROUP BY for performance
    results = (
        db.session.query(ExpenseCategory.name, func.sum(Expense.amount))
        .join(ExpenseCategory, Expense.category_id == ExpenseCategory.id)
        .filter(Expense.business_id == g.business_id)
        .group_by(ExpenseCategory.name)
        .all()
    )

    # Handle uncategorized expenses
    uncategorized_total = db.session.query(
        func.sum(Expense.amount)
    ).filter(
        Expense.business_id == g.business_id, 
        Expense.category_id == None
    ).scalar() or Decimal("0.00")

    category_totals = {name: total for name, total in results}
    if uncategorized_total > 0:
        category_totals["Uncategorized"] = uncategorized_total

    sorted_categories = sorted(category_totals.items(), key=lambda x: x[1], reverse=True)
    total = sum(category_totals.values(), Decimal("0.00"))
    
    return render_template(
        "expenses/summary.html",
        category_totals=sorted_categories,
        total=total
    )

@expenses_bp.route("/")
@login_required
def list():
    query = scoped(Expense)

    category_id = request.args.get("category_id", type=int)
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    if category_id:
        query = query.filter(Expense.category_id == category_id)
    if start_date:
        query = query.filter(Expense.date >= start_date)
    if end_date:
        query = query.filter(Expense.date <= end_date)

    expenses = query.order_by(Expense.date.desc()).all()
    total = query.with_entities(func.sum(Expense.amount)).scalar() or Decimal("0.00")
    categories = scoped(ExpenseCategory).order_by(ExpenseCategory.name).all()

    return render_template(
        "expenses/list.html",
        expenses=expenses,
        total=total,
        categories=categories,
        selected_category=category_id,
        start_date=start_date or "",
        end_date=end_date or "",
    )


@expenses_bp.route("/new", methods=["GET", "POST"])
@login_required
def new():
    categories = scoped(ExpenseCategory).order_by(ExpenseCategory.name).all()
    suppliers = scoped(Contact).filter_by(type="supplier").order_by(Contact.name).all()

    if request.method == "POST":
        error = None
        amount, amount_error = _parse_amount(request.form.get("amount", "0"))
        if amount_error:
            error = amount_error

        expense_date_str = request.form.get("date", "").strip()
        try:
            expense_date = datetime.strptime(expense_date_str, "%Y-%m-%d").date()
        except ValueError:
            error = "Enter a valid date."
            expense_date = None

        category_id, supplier_id, ref_error = _validate_expense_refs(
            request.form.get("category_id"), request.form.get("supplier_id")
        )
        if ref_error and not error:
            error = ref_error

        if error:
            flash(error, "error")
            return render_template("expenses/form.html", expense=None, categories=categories, suppliers=suppliers)

        expense = Expense(
            business_id=g.business_id,
            category_id=category_id,
            supplier_id=supplier_id,
            date=expense_date,
            amount=amount,
            description=request.form.get("description", "").strip() or None,
        )
        db.session.add(expense)
        db.session.commit()
        flash("Expense logged.", "success")
        return redirect(url_for("expenses.list"))

    return render_template("expenses/form.html", expense=None, categories=categories, suppliers=suppliers, today=date.today().isoformat())


@expenses_bp.route("/<int:expense_id>/edit", methods=["GET", "POST"])
@login_required
def edit(expense_id):
    expense = scoped(Expense).filter_by(id=expense_id).first_or_404()
    categories = scoped(ExpenseCategory).order_by(ExpenseCategory.name).all()
    suppliers = scoped(Contact).filter_by(type="supplier").order_by(Contact.name).all()

    if request.method == "POST":
        error = None
        amount, amount_error = _parse_amount(request.form.get("amount", "0"))
        if amount_error:
            error = amount_error

        expense_date_str = request.form.get("date", "").strip()
        try:
            expense_date = datetime.strptime(expense_date_str, "%Y-%m-%d").date()
        except ValueError:
            error = "Enter a valid date."
            expense_date = None

        category_id, supplier_id, ref_error = _validate_expense_refs(
            request.form.get("category_id"), request.form.get("supplier_id")
        )
        if ref_error and not error:
            error = ref_error

        if error:
            flash(error, "error")
            return render_template("expenses/form.html", expense=expense, categories=categories, suppliers=suppliers)

        expense.category_id = category_id
        expense.supplier_id = supplier_id
        expense.date = expense_date
        expense.amount = amount
        expense.description = request.form.get("description", "").strip() or None

        db.session.commit()
        flash("Expense updated.", "success")
        return redirect(url_for("expenses.list"))

    return render_template("expenses/form.html", expense=expense, categories=categories, suppliers=suppliers)


@expenses_bp.route("/<int:expense_id>/delete", methods=["POST"])
@login_required
def delete(expense_id):
    expense = scoped(Expense).filter_by(id=expense_id).first_or_404()
    db.session.delete(expense)
    db.session.commit()
    flash("Expense deleted.", "success")
    return redirect(url_for("expenses.list"))
