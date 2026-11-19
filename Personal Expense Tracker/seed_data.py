"""
Sample Demonstration Data Seeder.
Creates a demo user with realistic multi-category income, expenses, and budgets
to easily evaluate and showcase the application during college project reviews or viva.
"""

from datetime import datetime, timedelta
from database import db
from features.auth import AuthService
from features.income import IncomeService
from features.expenses import ExpenseService
from features.budget import BudgetService
from features.categories import CategoryService
from utils.validators import parse_amount_to_paise


def seed_demo_data(verbose: bool = True) -> tuple[bool, str]:
    """
    Seed a demonstration account with realistic financial entries.
    Demo Credentials:
      Username: demo_user
      Password: Password123
    """
    auth = AuthService(db)
    income_service = IncomeService(db)
    expense_service = ExpenseService(db)
    budget_service = BudgetService(db)
    cat_service = CategoryService(db)

    # Check if demo_user already exists
    existing = db.fetch_one("SELECT user_id FROM users WHERE username = 'demo_user';")
    if existing:
        if verbose:
            print("[i] Demo account 'demo_user' already exists.")
        return True, "Demo account already exists."

    # Register demo user
    success, msg, user = auth.register("demo_user", "demo@college.edu", "Password123")
    if not success or not user:
        return False, f"Failed to create demo user: {msg}"

    user_id = user.user_id
    if verbose:
        print(f"[+] Created user: {user.username} (ID: {user_id})")

    # Add custom categories for demo user
    cat_service.add_category(user_id, "Gym & Fitness", "EXPENSE")
    cat_service.add_category(user_id, "Books & Courses", "EXPENSE")

    # Fetch category maps
    income_cats = {
        c["category_name"].lower(): c["category_id"]
        for c in cat_service.get_categories(user_id, "INCOME")
    }
    expense_cats = {
        c["category_name"].lower(): c["category_id"]
        for c in cat_service.get_categories(user_id, "EXPENSE")
    }

    # Helper dates
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    day_before = today - timedelta(days=2)
    last_week = today - timedelta(days=7)

    # 1. Income entries
    sample_incomes = [
        ("salary", "75000.00", today.strftime("%Y-%m-%d"), "Monthly Software Engineering Salary"),
        ("freelancing", "22500.00", yesterday.strftime("%Y-%m-%d"), "Mobile App UI Design Project"),
        ("investment", "4200.50", last_week.strftime("%Y-%m-%d"), "Mutual Fund Dividend Payout"),
        ("other", "3000.00", day_before.strftime("%Y-%m-%d"), "Cashback and Birthday Gift"),
    ]

    for cat_name, amt_str, dt_str, desc in sample_incomes:
        cat_id = income_cats.get(cat_name)
        if cat_id:
            _, paise, _ = parse_amount_to_paise(amt_str)
            income_service.add_income(user_id, cat_id, paise, dt_str, desc)

    # 2. Expense entries
    sample_expenses = [
        ("bills", "18500.00", today.strftime("%Y-%m-%d"), "Apartment Monthly Rent"),
        ("food", "6450.00", today.strftime("%Y-%m-%d"), "Monthly Supermarket Groceries"),
        ("travel", "3200.00", yesterday.strftime("%Y-%m-%d"), "Monthly Metro Card & Fuel"),
        ("bills", "2400.00", yesterday.strftime("%Y-%m-%d"), "Electricity & Water Utility Bill"),
        ("entertainment", "1499.00", day_before.strftime("%Y-%m-%d"), "Netflix and Spotify Subscriptions"),
        ("shopping", "4850.50", day_before.strftime("%Y-%m-%d"), "Formal Office Attire"),
        ("medical", "1800.00", last_week.strftime("%Y-%m-%d"), "Dental Consultation and Medicines"),
        ("education", "3500.00", last_week.strftime("%Y-%m-%d"), "Cloud Certification Exam Fee"),
        ("gym & fitness", "2500.00", today.strftime("%Y-%m-%d"), "Annual Gym Membership Installment"),
    ]

    for cat_name, amt_str, dt_str, desc in sample_expenses:
        cat_id = expense_cats.get(cat_name)
        if cat_id:
            _, paise, _ = parse_amount_to_paise(amt_str)
            expense_service.add_expense(user_id, cat_id, paise, dt_str, desc)

    # 3. Set Monthly Budget
    # Total expense above is ~₹44,699.50.
    # Set budget to ₹50,000.00 (which is ~89.4% used, triggering the 80% warning alert!)
    _, budget_paise, _ = parse_amount_to_paise("50000.00")
    budget_service.set_or_update_budget(user_id, today.month, today.year, budget_paise)

    if verbose:
        print("[+] Seeded sample income, expenses, and monthly budget for demo_user.")
        print("[+] Demo account is ready for demonstration!")

    return True, "Demo data successfully seeded!"


if __name__ == "__main__":
    seed_demo_data()
