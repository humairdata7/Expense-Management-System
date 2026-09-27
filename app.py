from flask import Flask, render_template, request, redirect, url_for,flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from datetime import datetime

app = Flask(__name__)

app.secret_key = "expense-crud-secret"

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///expense.db"

db = SQLAlchemy(app)

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(100), nullable=False)
    date = db.Column(db.String(20), nullable=False)
#Database table agr create nahi hoi to vo create krna
#app.app_context() Flask application ke database/config environment ko temporarily active karta hai.
with app.app_context():
    db.create_all()    
#Route hamain btata hai k konsa url work kry ga
@app.route("/")
def home():

    # Total expense amount
    total_expense = db.session.query(
        func.sum(Expense.amount)
    ).scalar() or 0

    # Total expense records
    total_records = Expense.query.count()

    # Total unique categories
    total_categories = db.session.query(
        func.count(
            func.distinct(
                func.lower(
                    func.trim(Expense.category)
                )
            )
        )
    ).scalar() or 0

    # Current month
    current_month = datetime.now().strftime("%Y-%m")

    # Current month expense
    this_month_expense = db.session.query(
        func.sum(Expense.amount)
    ).filter(
        Expense.date.like(f"{current_month}%")
    ).scalar() or 0
    
    # Latest 5 expenses
    recent_expenses = Expense.query.order_by(
        Expense.date.desc(),
        Expense.id.desc()
    ).limit(5).all()
    
    return render_template(
        "index.html",
        total_expense=total_expense,
        total_records=total_records,
        total_categories=total_categories,
        this_month_expense=this_month_expense,
        recent_expenses=recent_expenses
    )
@app.route("/expenses")
def expenses_page():

    search = request.args.get("search", "").strip()

    query = Expense.query

    if search:
        query = query.filter(
            Expense.name.ilike(f"%{search}%")
        )

    page = request.args.get("page", 1, type=int)

    pagination = query.order_by(
        Expense.id.asc()
    ).paginate(
        page=page,
        per_page=5,
        error_out=False
    )

    expenses = pagination.items

    return render_template(
        "expenses.html",
        expenses=expenses,
        pagination=pagination,
        search=search
    )

@app.route("/add-expense")
def add_expense_page():
    return render_template("add_expense.html")


@app.route("/filters")
def filters_page():

    search = request.args.get("search", "").strip()
    category = request.args.get("category", "").strip()
    sort = request.args.get("sort", "")
    start_date = request.args.get("start_date", "")
    end_date = request.args.get("end_date", "")

    query = Expense.query

    if search:
        query = query.filter(
            Expense.name.ilike(f"%{search}%")
        )

    if category:
        query = query.filter(
            func.lower(func.trim(Expense.category)) == category.lower()
        )

    if start_date:
        query = query.filter(
            Expense.date >= start_date
        )

    if end_date:
        query = query.filter(
            Expense.date <= end_date
        )

    if sort == "name":
        query = query.order_by(Expense.name.asc())

    elif sort == "amount_low":
        query = query.order_by(Expense.amount.asc())

    elif sort == "amount_high":
        query = query.order_by(Expense.amount.desc())

    elif sort == "date":
        query = query.order_by(Expense.date.desc())

    page = request.args.get("page", 1, type=int)

    pagination = query.paginate(
        page=page,
        per_page=5,
        error_out=False
    )

    expenses = pagination.items

    raw_categories = db.session.query(
        Expense.category
    ).all()

    categories = []

    for row in raw_categories:
        item = row[0].strip()

        if item.lower() not in [c.lower() for c in categories]:
            categories.append(item)

    return render_template(
        "filters.html",
        expenses=expenses,
        pagination=pagination,
        search=search,
        category=category,
        sort=sort,
        start_date=start_date,
        end_date=end_date,
        categories=categories
    )


@app.route("/reports")
def reports_page():

    # Category wise report
    category_report = db.session.query(
        Expense.category,
        func.sum(Expense.amount),
        func.count(Expense.id)
    ).group_by(
        Expense.category
    ).order_by(
        func.sum(Expense.amount).desc()
    ).all()


    # Category chart data
    category_labels = []
    category_amounts = []

    for item in category_report:
        category_labels.append(item[0])
        category_amounts.append(float(item[1]))


    # Month wise report
    month_report = db.session.query(
        func.substr(Expense.date, 1, 7),
        func.sum(Expense.amount),
        func.count(Expense.id)
    ).group_by(
        func.substr(Expense.date, 1, 7)
    ).order_by(
        func.substr(Expense.date, 1, 7).asc()
    ).all()


    # Monthly chart data
    month_labels = []
    month_amounts = []

    for item in month_report:
        month_labels.append(item[0])
        month_amounts.append(float(item[1]))


    return render_template(
        "reports.html",
        category_report=category_report,
        month_report=month_report,
        category_labels=category_labels,
        category_amounts=category_amounts,
        month_labels=month_labels,
        month_amounts=month_amounts
    )

@app.route("/add", methods=["POST"])
def add_expense():
    #falsk form ki value reques.form.grt k through le
    name = request.form.get("name").strip()
    amount = request.form.get("amount")
    try:
        amount = float(amount)
    except ValueError:
        flash("Please enter a valid amount")
        return redirect(url_for("home"))

    if amount <= 0:
        flash("Amount must be greater than 0")
        return redirect(url_for("home"))
    category = request.form.get("category").strip().title()
    date = request.form.get("date")
    if not name:
        flash("Expense name is required")
        return redirect(url_for("home"))

    if not category:
        flash("Category is required")
        return redirect(url_for("home"))

    if not date:
        flash("Date is required")
        return redirect(url_for("home"))

    new_expense = Expense(
        name=name,
        amount=amount,
        category=category,
        date=date
    )
    db.session.add(new_expense)
    db.session.commit()
    flash("Expense added successfully")

    return redirect(url_for("home"))

@app.route("/delete/<int:id>")
def delete_expense(id):

    expense = Expense.query.get_or_404(id)

    db.session.delete(expense)
    db.session.commit()
    flash("Expense deleted successfully")

    return redirect(url_for("home"))  

@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit_expense(id):

    expense = Expense.query.get_or_404(id)

    if request.method == "POST":

        name = request.form.get("name").strip()
        amount = request.form.get("amount")
        category = request.form.get("category").strip().title()
        date = request.form.get("date")

        if not name:
            flash("Expense name is required")
            return redirect(url_for("edit_expense", id=id))

        if not category:
            flash("Category is required")
            return redirect(url_for("edit_expense", id=id))

        if not date:
            flash("Date is required")
            return redirect(url_for("edit_expense", id=id))

        try:
            amount = float(amount)
        except ValueError:
            flash("Please enter a valid amount")
            return redirect(url_for("edit_expense", id=id))

        if amount <= 0:
            flash("Amount must be greater than 0")
            return redirect(url_for("edit_expense", id=id))

        expense.name = name
        expense.amount = amount
        expense.category = category
        expense.date = date

        db.session.commit()

        flash("Expense updated successfully")

        return redirect(url_for("home"))

    return render_template("edit.html", expense=expense) 

if __name__ == "__main__":
    app.run(debug=True)