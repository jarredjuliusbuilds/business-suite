from flask import Blueprint, render_template, redirect, url_for, flash, request, g
from flask_login import login_required
from datetime import datetime
from app.extensions import db
from app.models import Task, Contact
from app.utils import scoped

tasks_bp = Blueprint("tasks", __name__, url_prefix="/tasks")


@tasks_bp.route("/")
@login_required
def list():
    show_done = request.args.get("show_done") == "1"
    query = scoped(Task)
    if not show_done:
        query = query.filter(Task.status == "open")
    tasks = query.order_by(Task.due_date.asc().nullslast(), Task.created_at.desc()).all()
    return render_template("tasks/list.html", tasks=tasks, show_done=show_done)


@tasks_bp.route("/new", methods=["GET", "POST"])
@login_required
def new():
    contacts = scoped(Contact).order_by(Contact.name).all()

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        if not title:
            flash("Title is required.", "error")
            return render_template("tasks/form.html", task=None, contacts=contacts)

        due_date_str = request.form.get("due_date", "").strip()
        due_date = None
        if due_date_str:
            try:
                due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()
            except ValueError:
                flash("Enter a valid date.", "error")
                return render_template("tasks/form.html", task=None, contacts=contacts)

        task = Task(
            business_id=g.business_id,
            contact_id=request.form.get("contact_id") or None,
            title=title,
            due_date=due_date,
        )
        db.session.add(task)
        db.session.commit()
        flash("Task added.", "success")
        return redirect(url_for("tasks.list"))

    return render_template("tasks/form.html", task=None, contacts=contacts)


@tasks_bp.route("/<int:task_id>/toggle", methods=["POST"])
@login_required
def toggle(task_id):
    task = scoped(Task).filter_by(id=task_id).first_or_404()
    task.status = "done" if task.status == "open" else "open"
    db.session.commit()
    return redirect(url_for("tasks.list"))


@tasks_bp.route("/<int:task_id>/edit", methods=["GET", "POST"])
@login_required
def edit(task_id):
    task = scoped(Task).filter_by(id=task_id).first_or_404()
    contacts = scoped(Contact).order_by(Contact.name).all()

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        if not title:
            flash("Title is required.", "error")
            return render_template("tasks/form.html", task=task, contacts=contacts)

        due_date_str = request.form.get("due_date", "").strip()
        due_date = None
        if due_date_str:
            try:
                due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()
            except ValueError:
                flash("Enter a valid date.", "error")
                return render_template("tasks/form.html", task=task, contacts=contacts)

        task.title = title
        task.due_date = due_date
        task.contact_id = request.form.get("contact_id") or None
        db.session.commit()
        flash("Task updated.", "success")
        return redirect(url_for("tasks.list"))

    return render_template("tasks/form.html", task=task, contacts=contacts)


@tasks_bp.route("/<int:task_id>/delete", methods=["POST"])
@login_required
def delete(task_id):
    task = scoped(Task).filter_by(id=task_id).first_or_404()
    db.session.delete(task)
    db.session.commit()
    flash("Task deleted.", "success")
    return redirect(url_for("tasks.list"))
