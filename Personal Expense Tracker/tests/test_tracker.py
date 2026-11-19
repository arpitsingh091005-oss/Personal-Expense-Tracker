"""
Comprehensive Unit Test Suite for Personal Expense Tracker.
Uses Python's standard unittest framework.
Tests authentication, CRUD operations, budget tracking, validations,
data isolation, reports, and CSV export.
"""

import os
import unittest
import tempfile
from pathlib import Path
from database import DatabaseManager
from features.auth import AuthService
from features.categories import CategoryService
from features.income import IncomeService
from features.expenses import ExpenseService
from features.budget import BudgetService
from features.dashboard import DashboardService
from features.reports import ReportService
from utils.validators import (
    validate_username,
    validate_email,
    validate_password,
    parse_amount_to_paise,
    validate_date,
    validate_month_year,
)


class TestPersonalExpenseTracker(unittest.TestCase):
    """Test suite covering all requirements of the Personal Expense Tracker."""

    def setUp(self):
        """Create a fresh temporary SQLite database for each test case."""
        self.temp_db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db_path = Path(self.temp_db_file.name)
        self.temp_db_file.close()

        self.db = DatabaseManager(self.temp_db_path)
        self.auth = AuthService(self.db)
        self.categories = CategoryService(self.db)
        self.income = IncomeService(self.db)
        self.expenses = ExpenseService(self.db)
        self.budget = BudgetService(self.db)
        self.dashboard = DashboardService(self.db)
        self.reports = ReportService(self.db)

        # Register a primary test user
        ok, msg, user = self.auth.register("testuser", "test@example.com", "Password123")
        self.assertTrue(ok)
        self.assertIsNotNone(user)
        self.user = user

    def tearDown(self):
        """Clean up the temporary database file after each test."""
        if self.temp_db_path.exists():
            try:
                os.remove(self.temp_db_path)
            except PermissionError:
                pass

    # -------------------------------------------------------------
    # 1. VALIDATION TESTS
    # -------------------------------------------------------------

    def test_validators(self):
        """Test username, email, password, amount, and date validators."""
        # Username
        self.assertTrue(validate_username("valid_user1")[0])
        self.assertFalse(validate_username("")[0])
        self.assertFalse(validate_username("ab")[0])  # too short
        self.assertFalse(validate_username("invalid user")[0])  # space

        # Email
        self.assertTrue(validate_email("user@domain.com")[0])
        self.assertFalse(validate_email("invalid-email")[0])
        self.assertFalse(validate_email("")[0])

        # Password
        self.assertTrue(validate_password("SecurePass1")[0])
        self.assertFalse(validate_password("123")[0])  # too short
        self.assertFalse(validate_password("      ")[0])  # whitespace

        # Amount to paise
        ok, paise, err = parse_amount_to_paise("150.75")
        self.assertTrue(ok)
        self.assertEqual(paise, 15075)

        ok, paise, err = parse_amount_to_paise("1000")
        self.assertTrue(ok)
        self.assertEqual(paise, 100000)

        self.assertFalse(parse_amount_to_paise("0")[0])  # zero rejected
        self.assertFalse(parse_amount_to_paise("-50")[0])  # negative rejected
        self.assertFalse(parse_amount_to_paise("abc")[0])  # non-numeric rejected

        # Date
        self.assertTrue(validate_date("2026-11-19")[0])
        self.assertFalse(validate_date("2026-02-30")[0])  # invalid calendar date
        self.assertFalse(validate_date("19/11/2026")[0])  # wrong format

        # Month and Year
        self.assertTrue(validate_month_year(11, 2026)[0])
        self.assertFalse(validate_month_year(13, 2026)[0])
        self.assertFalse(validate_month_year(0, 2026)[0])

    # -------------------------------------------------------------
    # 2. AUTHENTICATION TESTS
    # -------------------------------------------------------------

    def test_user_registration_duplicate_username(self):
        """Prevent duplicate username registration."""
        ok, msg, user = self.auth.register("testuser", "other@example.com", "Password123")
        self.assertFalse(ok)
        self.assertIn("already registered", msg.lower())

    def test_user_registration_duplicate_email(self):
        """Prevent duplicate email registration."""
        ok, msg, user = self.auth.register("otheruser", "test@example.com", "Password123")
        self.assertFalse(ok)
        self.assertIn("already registered", msg.lower())

    def test_user_login_success(self):
        """Test successful login with username or email."""
        ok, msg, user = self.auth.login("testuser", "Password123")
        self.assertTrue(ok)
        self.assertEqual(user.username, "testuser")

        # Test login via email
        ok, msg, user2 = self.auth.login("test@example.com", "Password123")
        self.assertTrue(ok)
        self.assertEqual(user2.user_id, self.user.user_id)

    def test_user_login_invalid_credentials(self):
        """Test login with wrong password or unknown user."""
        ok, msg, user = self.auth.login("testuser", "WrongPassword")
        self.assertFalse(ok)
        self.assertIsNone(user)

        ok, msg, user = self.auth.login("nonexistent", "Password123")
        self.assertFalse(ok)
        self.assertIsNone(user)

    def test_change_password(self):
        """Test password update and verification."""
        ok, msg = self.auth.change_password(self.user.user_id, "Password123", "NewSecret456")
        self.assertTrue(ok)

        # Login with old password must fail
        ok, msg, _ = self.auth.login("testuser", "Password123")
        self.assertFalse(ok)

        # Login with new password must succeed
        ok, msg, user = self.auth.login("testuser", "NewSecret456")
        self.assertTrue(ok)

    # -------------------------------------------------------------
    # 3. CATEGORY TESTS
    # -------------------------------------------------------------

    def test_default_categories_seeded(self):
        """Verify default system categories are automatically available."""
        cats = self.categories.get_categories(self.user.user_id)
        names = [c["category_name"] for c in cats]
        self.assertIn("Food", names)
        self.assertIn("Salary", names)
        self.assertIn("Bills", names)
        self.assertIn("Travel", names)

    def test_custom_category_creation_and_deletion(self):
        """Test adding and deleting custom categories."""
        ok, msg, cat_id = self.categories.add_category(
            self.user.user_id, "Freelance Writing", "INCOME"
        )
        self.assertTrue(ok)
        self.assertIsNotNone(cat_id)

        # Duplicate custom category should fail
        ok, msg, _ = self.categories.add_category(
            self.user.user_id, "Freelance Writing", "INCOME"
        )
        self.assertFalse(ok)

        # System default category cannot be deleted
        system_cat = self.categories.get_category_by_name("Food", "EXPENSE", self.user.user_id)
        ok, msg = self.categories.delete_category(self.user.user_id, system_cat["category_id"])
        self.assertFalse(ok)
        self.assertIn("cannot be deleted", msg)

        # Custom category can be deleted
        ok, msg = self.categories.delete_category(self.user.user_id, cat_id)
        self.assertTrue(ok)

    # -------------------------------------------------------------
    # 4. INCOME TESTS
    # -------------------------------------------------------------

    def test_income_crud(self):
        """Test recording, viewing, updating, and deleting income entries."""
        salary_cat = self.categories.get_category_by_name("Salary", "INCOME", self.user.user_id)
        self.assertIsNotNone(salary_cat)

        # Add income
        ok, msg, tx_id = self.income.add_income(
            self.user.user_id,
            salary_cat["category_id"],
            7500000,  # 75,000.00 INR
            "2026-11-01",
            "Monthly Base Salary",
        )
        self.assertTrue(ok)
        self.assertIsNotNone(tx_id)

        # View incomes
        incomes = self.income.get_incomes(self.user.user_id)
        self.assertEqual(len(incomes), 1)
        self.assertEqual(incomes[0]["amount"], 7500000)

        # Update income
        other_cat = self.categories.get_category_by_name("Other", "INCOME", self.user.user_id)
        ok, msg = self.income.update_income(
            self.user.user_id,
            tx_id,
            other_cat["category_id"],
            8000000,
            "2026-11-02",
            "Revised Base Salary",
        )
        self.assertTrue(ok)

        updated = self.income.get_income_by_id(self.user.user_id, tx_id)
        self.assertEqual(updated["amount"], 8000000)
        self.assertEqual(updated["category_name"], "Other")

        # Delete income
        ok, msg = self.income.delete_income(self.user.user_id, tx_id)
        self.assertTrue(ok)
        self.assertEqual(len(self.income.get_incomes(self.user.user_id)), 0)

    # -------------------------------------------------------------
    # 5. EXPENSE & REAL-TIME BUDGET WARNING TESTS
    # -------------------------------------------------------------

    def test_expense_crud_and_budget_warnings(self):
        """Test recording expense and verifying 80% and exceeded budget triggers."""
        # Set a monthly budget of ₹10,000.00 (1,000,000 paise) for Nov 2026
        self.budget.set_or_update_budget(self.user.user_id, 11, 2026, 1000000)

        food_cat = self.categories.get_category_by_name("Food", "EXPENSE", self.user.user_id)

        # 1. Add expense ₹5,000 (50% used) -> No warning
        ok, msg, tx1, warning = self.expenses.add_expense(
            self.user.user_id, food_cat["category_id"], 500000, "2026-11-05", "Groceries"
        )
        self.assertTrue(ok)
        self.assertIsNone(warning)

        # 2. Add expense ₹3,500 (Total spent: ₹8,500 = 85%) -> 80% Threshold Warning
        ok, msg, tx2, warning = self.expenses.add_expense(
            self.user.user_id, food_cat["category_id"], 350000, "2026-11-10", "Dinner"
        )
        self.assertTrue(ok)
        self.assertIsNotNone(warning)
        self.assertIn("80% BUDGET THRESHOLD REACHED", warning)

        # 3. Add expense ₹2,000 (Total spent: ₹10,500 = 105%) -> Budget Exceeded Alert
        ok, msg, tx3, warning = self.expenses.add_expense(
            self.user.user_id, food_cat["category_id"], 200000, "2026-11-15", "Parties"
        )
        self.assertTrue(ok)
        self.assertIsNotNone(warning)
        self.assertIn("BUDGET EXCEEDED", warning)

        # Verify negative amount rejected
        ok, msg, _, _ = self.expenses.add_expense(
            self.user.user_id, food_cat["category_id"], -100, "2026-11-15", "Invalid"
        )
        self.assertFalse(ok)

        # Delete expense
        ok, msg = self.expenses.delete_expense(self.user.user_id, tx3)
        self.assertTrue(ok)

    # -------------------------------------------------------------
    # 6. BUDGET MANAGEMENT TESTS
    # -------------------------------------------------------------

    def test_budget_upsert_and_calculations(self):
        """Test setting, updating duplicate month, and calculation metrics."""
        # Set budget ₹20,000
        ok, msg, b_id = self.budget.set_or_update_budget(self.user.user_id, 12, 2026, 2000000)
        self.assertTrue(ok)

        # Update budget for same month (no duplicate entry)
        ok, msg, b_id2 = self.budget.set_or_update_budget(self.user.user_id, 12, 2026, 2500000)
        self.assertTrue(ok)
        self.assertIn("updated", msg)

        # Check total budgets count is 1
        budgets = self.budget.get_all_budgets(self.user.user_id)
        self.assertEqual(len(budgets), 1)
        self.assertEqual(budgets[0]["budget_amount"], 2500000)

    # -------------------------------------------------------------
    # 7. DASHBOARD & FINANCIAL CALCULATIONS TESTS
    # -------------------------------------------------------------

    def test_dashboard_calculations(self):
        """Verify Balance = Income - Expenses, Highest/Lowest Expenses, and Savings."""
        salary_cat = self.categories.get_category_by_name("Salary", "INCOME", self.user.user_id)
        travel_cat = self.categories.get_category_by_name("Travel", "EXPENSE", self.user.user_id)
        food_cat = self.categories.get_category_by_name("Food", "EXPENSE", self.user.user_id)

        # Income: ₹50,000 (5,000,000 paise)
        self.income.add_income(
            self.user.user_id, salary_cat["category_id"], 5000000, "2026-11-01", "Paycheck"
        )

        # Expense 1: ₹1,500 (150,000 paise)
        self.expenses.add_expense(
            self.user.user_id, food_cat["category_id"], 150000, "2026-11-05", "Snacks"
        )
        # Expense 2: ₹12,000 (1,200,000 paise)
        self.expenses.add_expense(
            self.user.user_id, travel_cat["category_id"], 1200000, "2026-11-10", "Train Tickets"
        )

        summary = self.dashboard.get_financial_summary(self.user.user_id, month=11, year=2026)

        # Total Income = ₹50,000
        self.assertEqual(summary["total_income"], 5000000)
        # Total Expense = ₹13,500
        self.assertEqual(summary["total_expenses"], 1350000)
        # Balance = ₹36,500
        self.assertEqual(summary["balance"], 3650000)
        # Monthly Savings = ₹36,500
        self.assertEqual(summary["monthly_savings"], 3650000)

        # Highest expense = Travel (₹12,000)
        self.assertEqual(summary["highest_expense"]["amount"], 1200000)
        self.assertEqual(summary["highest_expense"]["category_name"], "Travel")

        # Lowest expense = Food (₹1,500)
        self.assertEqual(summary["lowest_expense"]["amount"], 150000)
        self.assertEqual(summary["lowest_expense"]["category_name"], "Food")

    # -------------------------------------------------------------
    # 8. REPORTS & CSV EXPORT TESTS
    # -------------------------------------------------------------

    def test_reports_and_csv_export(self):
        """Test daily, monthly, yearly, category reports and CSV file export."""
        salary_cat = self.categories.get_category_by_name("Salary", "INCOME", self.user.user_id)
        food_cat = self.categories.get_category_by_name("Food", "EXPENSE", self.user.user_id)

        self.income.add_income(
            self.user.user_id, salary_cat["category_id"], 2000000, "2026-11-19", "Bonus"
        )
        self.expenses.add_expense(
            self.user.user_id, food_cat["category_id"], 40000, "2026-11-19", "Lunch"
        )

        # Daily report
        daily = self.reports.get_daily_report(self.user.user_id, "2026-11-19")
        self.assertEqual(daily["total_income"], 2000000)
        self.assertEqual(daily["total_expenses"], 40000)
        self.assertEqual(daily["net_balance"], 1960000)

        # Monthly report
        monthly = self.reports.get_monthly_report(self.user.user_id, 11, 2026)
        self.assertEqual(monthly["total_income"], 2000000)
        self.assertEqual(monthly["total_expenses"], 40000)

        # CSV Export
        temp_csv = tempfile.NamedTemporaryFile(suffix=".csv", delete=False)
        temp_csv_path = Path(temp_csv.name)
        temp_csv.close()

        ok, msg, path = self.reports.export_transactions_to_csv(
            self.user.user_id, custom_filepath=temp_csv_path
        )
        self.assertTrue(ok)
        self.assertTrue(os.path.exists(path))

        with open(path, mode="r", encoding="utf-8") as f:
            lines = f.readlines()
            # 1 header line + 2 transaction lines
            self.assertEqual(len(lines), 3)
            self.assertIn("Transaction ID,Date,Type,Category,Amount (INR)", lines[0])
            self.assertIn("Bonus", "".join(lines))
            self.assertIn("Lunch", "".join(lines))

        if os.path.exists(path):
            os.remove(path)

    # -------------------------------------------------------------
    # 9. USER DATA ISOLATION TESTS
    # -------------------------------------------------------------

    def test_strict_user_data_isolation(self):
        """Ensure User A cannot view, edit, or delete User B's financial data."""
        # Create User B
        ok, _, user_b = self.auth.register("second_user", "second@example.com", "Password123")
        self.assertTrue(ok)

        salary_cat = self.categories.get_category_by_name("Salary", "INCOME", self.user.user_id)
        food_cat = self.categories.get_category_by_name("Food", "EXPENSE", self.user.user_id)

        # User A creates income and expense
        _, _, inc_a = self.income.add_income(
            self.user.user_id, salary_cat["category_id"], 1000000, "2026-11-19", "User A Income"
        )
        _, _, exp_a, _ = self.expenses.add_expense(
            self.user.user_id, food_cat["category_id"], 300000, "2026-11-19", "User A Expense"
        )

        # User B should see 0 incomes and 0 expenses
        b_incomes = self.income.get_incomes(user_b.user_id)
        self.assertEqual(len(b_incomes), 0)

        b_expenses = self.expenses.get_expenses(user_b.user_id)
        self.assertEqual(len(b_expenses), 0)

        # User B cannot access User A's income by ID
        isolated_inc = self.income.get_income_by_id(user_b.user_id, inc_a)
        self.assertIsNone(isolated_inc)

        # User B cannot update User A's income
        ok_upd, _ = self.income.update_income(
            user_b.user_id, inc_a, salary_cat["category_id"], 999999, "2026-11-19", "Hacked"
        )
        self.assertFalse(ok_upd)

        # User B cannot delete User A's expense
        ok_del, _ = self.expenses.delete_expense(user_b.user_id, exp_a)
        self.assertFalse(ok_del)

        # Record of User A remains intact
        a_exp = self.expenses.get_expense_by_id(self.user.user_id, exp_a)
        self.assertIsNotNone(a_exp)

    # -------------------------------------------------------------
    # 10. PERSISTENCE ACROSS RECONNECT
    # -------------------------------------------------------------

    def test_database_persistence_across_reconnect(self):
        """Verify data remains stored and consistent when closing and re-opening DB."""
        salary_cat = self.categories.get_category_by_name("Salary", "INCOME", self.user.user_id)
        self.income.add_income(
            self.user.user_id, salary_cat["category_id"], 5500000, "2026-11-10", "Persistent Income"
        )

        # Instantiate brand new DatabaseManager on the same file path
        new_db = DatabaseManager(self.temp_db_path)
        new_income_svc = IncomeService(new_db)

        rows = new_income_svc.get_incomes(self.user.user_id)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["description"], "Persistent Income")
        self.assertEqual(rows[0]["amount"], 5500000)


if __name__ == "__main__":
    unittest.main()
