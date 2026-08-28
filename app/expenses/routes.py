from flask import Blueprint, render_template, redirect, url_for, flash, request, g
from flask_login import login_required
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from app.extensions import db
from app.models import Expense, ExpenseCategory, Contact
from app.utils import scoped

expenses_bp = Blueprint("expenses", __name__, url_prefix="/expenses")


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
    total = sum((e.amount for e in expenses), Decimal("0.00"))
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
        try:
            amount = Decimal(request.form.get("amount", "0").strip())
        except InvalidOperation:
            error = "Enter a valid amount."
            amount = None

        expense_date_str = request.form.get("date", "").strip()
        try:
            expense_date = datetime.strptime(expense_date_str, "%Y-%m-%d").date()
        except ValueError:
            error = "Enter a valid date."
            expense_date = None

        if error:
            flash(error, "error")
            return render_template("expenses/form.html", expense=None, categories=categories, suppliers=suppliers)

        expense = Expense(
            business_id=g.business_id,
            category_id=request.form.get("category_id") or None,
            supplier_id=request.form.get("supplier_id") or None,
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
        try:
            amount = Decimal(request.form.get("amount", "0").strip())
        except InvalidOperation:
            error = "Enter a valid amount."
            amount = None

        expense_date_str = request.form.get("date", "").strip()
        try:
            expense_date = datetime.strptime(expense_date_str, "%Y-%m-%d").date()
        except ValueError:
            error = "Enter a valid date."
            expense_date = None

        if error:
            flash(error, "error")
            return render_template("expenses/form.html", expense=expense, categories=categories, suppliers=suppliers)

        expense.category_id = request.form.get("category_id") or None
        expense.supplier_id = request.form.get("supplier_id") or None
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
