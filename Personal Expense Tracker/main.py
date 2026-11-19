"""
Main Application Entry Point.
Personal Expense Tracker - Terminal User Interface.
MCA 3rd Year College Minor Project.
"""

import sys
from datetime import datetime
from config import APP_TITLE, APP_SUBTITLE, APP_VERSION
from database import db
from features.auth import AuthService, User
from features.categories import CategoryService
from features.income import IncomeService
from features.expenses import ExpenseService
from features.budget import BudgetService
from features.dashboard import DashboardService
from features.reports import ReportService
from seed_data import seed_demo_data
from utils.validators import (
    validate_username,
    validate_email,
    validate_password,
    parse_amount_to_paise,
    validate_date,
    validate_month_year,
)
from utils.helpers import (
    paise_to_rupees,
    format_currency,
    format_date,
    print_header,
    print_table,
    print_alert,
    print_success,
    print_error,
    get_input,
    pause,
)


class ExpenseTrackerApp:
    """
    Main controller for the Personal Expense Tracker CLI application.
    Manages session state, menu routing, user inputs, and service delegations.
    """

    def __init__(self):
        self.db = db
        self.auth = AuthService(self.db)
        self.categories = CategoryService(self.db)
        self.income = IncomeService(self.db)
        self.expenses = ExpenseService(self.db)
        self.budget = BudgetService(self.db)
        self.dashboard = DashboardService(self.db)
        self.reports = ReportService(self.db)
        self.current_user: User | None = None

    def run(self):
        """Main application lifecycle loop."""
        while True:
            try:
                if not self.current_user:
                    self.show_pre_login_menu()
                else:
                    self.show_main_menu()
            except (KeyboardInterrupt, EOFError):
                print("\n\nExiting application. Goodbye!")
                sys.exit(0)
            except Exception as e:
                print_error(f"An unexpected error occurred: {str(e)}")
                pause()

    # ---------------------------------------------------------
    # 1. PRE-LOGIN MENUS
    # ---------------------------------------------------------

    def show_pre_login_menu(self):
        """Displays registration, login, and demo seeder menu."""
        print_header(APP_TITLE, f"{APP_SUBTITLE} (v{APP_VERSION})")
        print("\n1. Register New Account")
        print("2. Login to Account")
        print("3. Seed Sample Demo Data (demo_user / Password123)")
        print("0. Exit Application")

        choice = get_input("\nEnter your choice")
        if choice == "1":
            self.handle_registration()
        elif choice == "2":
            self.handle_login()
        elif choice == "3":
            self.handle_seed_demo()
        elif choice == "0":
            print("\nThank you for using Personal Expense Tracker. Goodbye!")
            sys.exit(0)
        else:
            print_error("Invalid selection. Please choose an option from the menu.")
            pause()

    def handle_registration(self):
        """Registers a new user with input validation."""
        print_header("USER REGISTRATION", "Create a new personal account")
        print("[i] Type 'c' at any prompt to cancel.")

        username = get_input("Enter desired username", allow_cancel=True)
        if username is None:
            return
        valid_u, u_res = validate_username(username)
        if not valid_u:
            print_error(u_res)
            pause()
            return

        email = get_input("Enter your email address", allow_cancel=True)
        if email is None:
            return
        valid_e, e_res = validate_email(email)
        if not valid_e:
            print_error(e_res)
            pause()
            return

        password = get_input("Enter secure password (min 6 chars)", allow_cancel=True)
        if password is None:
            return
        valid_p, p_err = validate_password(password)
        if not valid_p:
            print_error(p_err)
            pause()
            return

        confirm_pwd = get_input("Confirm your password", allow_cancel=True)
        if confirm_pwd is None:
            return
        if password != confirm_pwd:
            print_error("Passwords do not match!")
            pause()
            return

        success, msg, user = self.auth.register(u_res, e_res, password)
        if success and user:
            print_success(msg)
            print_success(f"Account created for '{user.username}'. Please login to continue.")
        else:
            print_error(msg)
        pause()

    def handle_login(self):
        """Authenticates an existing user."""
        print_header("USER LOGIN", "Enter your credentials")
        identifier = get_input("Enter username or email", allow_cancel=True)
        if identifier is None:
            return

        password = get_input("Enter password", allow_cancel=True)
        if password is None:
            return

        success, msg, user = self.auth.login(identifier, password)
        if success and user:
            self.current_user = user
            print_success(f"Welcome back, {user.username}!")
            pause()
        else:
            print_error(msg)
            pause()

    def handle_seed_demo(self):
        """Populates the database with sample demonstration records."""
        print_header("SAMPLE DATA SEEDER", "Populating Demo Records")
        success, msg = seed_demo_data(verbose=True)
        if success:
            print_success(msg)
            print("\nYou can now login with:")
            print("  Username: demo_user")
            print("  Password: Password123")
        else:
            print_error(msg)
        pause()

    # ---------------------------------------------------------
    # 2. MAIN DASHBOARD MENU
    # ---------------------------------------------------------

    def show_main_menu(self):
        """Displays authenticated user main menu."""
        print_header(
            "MAIN DASHBOARD",
            f"Logged in as: {self.current_user.username} (ID: {self.current_user.user_id})",
        )
        print("\n1. Add Income")
        print("2. Add Expense")
        print("3. View & Manage Transactions")
        print("4. Manage Categories")
        print("5. Manage Monthly Budget")
        print("6. Financial Summary / Dashboard")
        print("7. Generate Reports")
        print("8. Export CSV Records")
        print("9. Change Password")
        print("10. Logout")
        print("0. Exit Application")

        choice = get_input("\nEnter your choice")
        if choice == "1":
            self.handle_add_income()
        elif choice == "2":
            self.handle_add_expense()
        elif choice == "3":
            self.handle_view_transactions_menu()
        elif choice == "4":
            self.handle_manage_categories()
        elif choice == "5":
            self.handle_manage_budget()
        elif choice == "6":
            self.handle_financial_summary()
        elif choice == "7":
            self.handle_reports_menu()
        elif choice == "8":
            self.handle_export_csv()
        elif choice == "9":
            self.handle_change_password()
        elif choice == "10":
            print_success(f"Logged out from account '{self.current_user.username}'.")
            self.current_user = None
            pause()
        elif choice == "0":
            print("\nThank you for using Personal Expense Tracker. Goodbye!")
            sys.exit(0)
        else:
            print_error("Invalid selection. Please choose an option from the menu.")
            pause()

    # ---------------------------------------------------------
    # 3. INCOME OPERATIONS
    # ---------------------------------------------------------

    def handle_add_income(self):
        """Prompt user and record new income entry."""
        print_header("ADD INCOME", "Record new income transaction")
        categories = self.categories.get_categories(self.current_user.user_id, "INCOME")
        if not categories:
            print_error("No income categories available. Please add a category first.")
            pause()
            return

        print("\nAvailable Income Categories:")
        for idx, cat in enumerate(categories, 1):
            ownership = f" ({cat['ownership']})" if "ownership" in cat.keys() else ""
            print(f"  {idx}. {cat['category_name']}{ownership}")

        cat_choice = get_input(f"Select category (1-{len(categories)})", allow_cancel=True)
        if cat_choice is None:
            return

        try:
            cat_idx = int(cat_choice) - 1
            if not (0 <= cat_idx < len(categories)):
                print_error("Invalid category selection.")
                pause()
                return
            selected_cat = categories[cat_idx]
        except ValueError:
            print_error("Invalid numeric choice.")
            pause()
            return

        # Amount
        amt_str = get_input("Enter amount in Rupees (e.g. 5000 or 12500.50)", allow_cancel=True)
        if amt_str is None:
            return
        valid_amt, amt_paise, amt_err = parse_amount_to_paise(amt_str)
        if not valid_amt:
            print_error(amt_err)
            pause()
            return

        # Date
        today_str = datetime.now().strftime("%Y-%m-%d")
        date_str = get_input(f"Enter transaction date [YYYY-MM-DD]", default=today_str, allow_cancel=True)
        if date_str is None:
            return
        valid_date, clean_date, date_err = validate_date(date_str)
        if not valid_date:
            print_error(date_err)
            pause()
            return

        # Description
        desc = get_input("Enter description (optional)", default="", allow_cancel=True)
        if desc is None:
            return

        success, msg, tx_id = self.income.add_income(
            self.current_user.user_id,
            selected_cat["category_id"],
            amt_paise,
            clean_date,
            desc,
        )

        if success:
            print_success(f"{msg} (Amount: {format_currency(amt_paise)})")
        else:
            print_error(msg)
        pause()

    # ---------------------------------------------------------
    # 4. EXPENSE OPERATIONS
    # ---------------------------------------------------------

    def handle_add_expense(self):
        """Prompt user and record new expense with real-time budget check."""
        print_header("ADD EXPENSE", "Record new expense transaction")
        categories = self.categories.get_categories(self.current_user.user_id, "EXPENSE")
        if not categories:
            print_error("No expense categories available. Please add a category first.")
            pause()
            return

        print("\nAvailable Expense Categories:")
        for idx, cat in enumerate(categories, 1):
            ownership = f" ({cat['ownership']})" if "ownership" in cat.keys() else ""
            print(f"  {idx}. {cat['category_name']}{ownership}")

        cat_choice = get_input(f"Select category (1-{len(categories)})", allow_cancel=True)
        if cat_choice is None:
            return

        try:
            cat_idx = int(cat_choice) - 1
            if not (0 <= cat_idx < len(categories)):
                print_error("Invalid category selection.")
                pause()
                return
            selected_cat = categories[cat_idx]
        except ValueError:
            print_error("Invalid numeric choice.")
            pause()
            return

        # Amount
        amt_str = get_input("Enter expense amount in Rupees (e.g. 250 or 1500.75)", allow_cancel=True)
        if amt_str is None:
            return
        valid_amt, amt_paise, amt_err = parse_amount_to_paise(amt_str)
        if not valid_amt:
            print_error(amt_err)
            pause()
            return

        # Date
        today_str = datetime.now().strftime("%Y-%m-%d")
        date_str = get_input(f"Enter transaction date [YYYY-MM-DD]", default=today_str, allow_cancel=True)
        if date_str is None:
            return
        valid_date, clean_date, date_err = validate_date(date_str)
        if not valid_date:
            print_error(date_err)
            pause()
            return

        # Description
        desc = get_input("Enter description (optional)", default="", allow_cancel=True)
        if desc is None:
            return

        success, msg, tx_id, warning = self.expenses.add_expense(
            self.current_user.user_id,
            selected_cat["category_id"],
            amt_paise,
            clean_date,
            desc,
        )

        if success:
            print_success(f"{msg} (Amount: {format_currency(amt_paise)})")
            if warning:
                print_alert(warning)
        else:
            print_error(msg)
        pause()

    # ---------------------------------------------------------
    # 5. VIEW & MANAGE TRANSACTIONS
    # ---------------------------------------------------------

    def handle_view_transactions_menu(self):
        """Submenu for viewing, filtering, updating, and deleting transactions."""
        while True:
            print_header("VIEW & MANAGE TRANSACTIONS")
            print("1. View All Transactions")
            print("2. View Incomes Only")
            print("3. View Expenses Only")
            print("4. Filter Transactions by Date Range")
            print("5. Search Transactions by Keyword")
            print("6. Update a Transaction")
            print("7. Delete a Transaction")
            print("0. Back to Main Dashboard")

            choice = get_input("\nEnter your choice")
            if choice == "1":
                self._display_transactions_table()
                pause()
            elif choice == "2":
                self._display_transactions_table(tx_type="INCOME")
                pause()
            elif choice == "3":
                self._display_transactions_table(tx_type="EXPENSE")
                pause()
            elif choice == "4":
                self._filter_transactions_by_date()
            elif choice == "5":
                self._search_transactions()
            elif choice == "6":
                self._handle_update_transaction()
            elif choice == "7":
                self._handle_delete_transaction()
            elif choice == "0":
                break
            else:
                print_error("Invalid selection.")
                pause()

    def _display_transactions_table(
        self,
        tx_type: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        search_term: str | None = None,
    ):
        """Helper to fetch and print transactions in formatted ASCII table."""
        u_id = self.current_user.user_id
        if tx_type == "INCOME":
            rows = self.income.get_incomes(
                u_id, start_date=start_date, end_date=end_date, search_term=search_term
            )
        elif tx_type == "EXPENSE":
            rows = self.expenses.get_expenses(
                u_id, start_date=start_date, end_date=end_date, search_term=search_term
            )
        else:
            # Combine all
            inc = self.income.get_incomes(
                u_id, start_date=start_date, end_date=end_date, search_term=search_term
            )
            exp = self.expenses.get_expenses(
                u_id, start_date=start_date, end_date=end_date, search_term=search_term
            )
            rows = sorted(
                list(inc) + list(exp),
                key=lambda x: (x["transaction_date"], x["transaction_id"]),
                reverse=True,
            )

        headers = ["ID", "Date", "Type", "Category", "Amount", "Description"]
        table_rows = []
        for r in rows:
            table_rows.append(
                [
                    r["transaction_id"],
                    r["transaction_date"],
                    r["transaction_type"],
                    r["category_name"],
                    format_currency(r["amount"]),
                    r["description"] or "-",
                ]
            )

        alignments = ["R", "L", "L", "L", "R", "L"]
        print_table(headers, table_rows, alignments=alignments)

    def _filter_transactions_by_date(self):
        """Filter transactions between start and end dates."""
        print_header("FILTER BY DATE RANGE")
        s_date = get_input("Enter Start Date [YYYY-MM-DD]", allow_cancel=True)
        if s_date is None:
            return
        valid_s, clean_s, err_s = validate_date(s_date)
        if not valid_s:
            print_error(err_s)
            pause()
            return

        e_date = get_input("Enter End Date [YYYY-MM-DD]", allow_cancel=True)
        if e_date is None:
            return
        valid_e, clean_e, err_e = validate_date(e_date)
        if not valid_e:
            print_error(err_e)
            pause()
            return

        if clean_s > clean_e:
            print_error("Start date cannot be after end date.")
            pause()
            return

        print(f"\nTransactions from {clean_s} to {clean_e}:")
        self._display_transactions_table(start_date=clean_s, end_date=clean_e)
        pause()

    def _search_transactions(self):
        """Search transactions by keyword in description or category name."""
        print_header("SEARCH TRANSACTIONS")
        term = get_input("Enter search keyword", allow_cancel=True)
        if term is None:
            return

        print(f"\nSearch results for '{term}':")
        self._display_transactions_table(search_term=term)
        pause()

    def _handle_update_transaction(self):
        """Update an existing income or expense entry."""
        print_header("UPDATE TRANSACTION")
        tx_id_str = get_input("Enter Transaction ID to update", allow_cancel=True)
        if tx_id_str is None:
            return

        try:
            tx_id = int(tx_id_str)
        except ValueError:
            print_error("Transaction ID must be an integer.")
            pause()
            return

        u_id = self.current_user.user_id
        # Check if income or expense
        tx = self.income.get_income_by_id(u_id, tx_id)
        is_income = True
        if not tx:
            tx = self.expenses.get_expense_by_id(u_id, tx_id)
            is_income = False

        if not tx:
            print_error(f"Transaction ID #{tx_id} not found in your records.")
            pause()
            return

        tx_type = tx["transaction_type"]
        current_amount_rupees = f"{paise_to_rupees(tx['amount']):.2f}"
        print(f"\nEditing {tx_type} #{tx_id}:")
        print(f"  Current Date:     {tx['transaction_date']}")
        print(f"  Current Category: {tx['category_name']}")
        print(f"  Current Amount:   {format_currency(tx['amount'])}")
        print(f"  Current Note:     {tx['description'] or '-'}")

        # Choose new or existing category
        categories = self.categories.get_categories(u_id, tx_type)
        print(f"\nSelect New Category for {tx_type} (press Enter to keep current):")
        for idx, cat in enumerate(categories, 1):
            marker = " *" if cat["category_id"] == tx["category_id"] else ""
            print(f"  {idx}. {cat['category_name']}{marker}")

        cat_choice = get_input(f"Choice (1-{len(categories)})", default="", allow_cancel=True)
        if cat_choice is None:
            return

        selected_cat_id = tx["category_id"]
        if cat_choice.strip():
            try:
                c_idx = int(cat_choice) - 1
                if 0 <= c_idx < len(categories):
                    selected_cat_id = categories[c_idx]["category_id"]
                else:
                    print_error("Invalid category choice.")
                    pause()
                    return
            except ValueError:
                print_error("Invalid category number.")
                pause()
                return

        # Amount
        amt_str = get_input("Enter new amount in Rupees", default=current_amount_rupees, allow_cancel=True)
        if amt_str is None:
            return
        valid_amt, amt_paise, amt_err = parse_amount_to_paise(amt_str)
        if not valid_amt:
            print_error(amt_err)
            pause()
            return

        # Date
        date_str = get_input("Enter new date [YYYY-MM-DD]", default=tx["transaction_date"], allow_cancel=True)
        if date_str is None:
            return
        valid_date, clean_date, date_err = validate_date(date_str)
        if not valid_date:
            print_error(date_err)
            pause()
            return

        # Description
        desc = get_input("Enter description", default=tx["description"] or "", allow_cancel=True)
        if desc is None:
            return

        if is_income:
            ok, msg = self.income.update_income(u_id, tx_id, selected_cat_id, amt_paise, clean_date, desc)
            if ok:
                print_success(msg)
            else:
                print_error(msg)
        else:
            ok, msg, warning = self.expenses.update_expense(
                u_id, tx_id, selected_cat_id, amt_paise, clean_date, desc
            )
            if ok:
                print_success(msg)
                if warning:
                    print_alert(warning)
            else:
                print_error(msg)
        pause()

    def _handle_delete_transaction(self):
        """Delete an income or expense record."""
        print_header("DELETE TRANSACTION")
        tx_id_str = get_input("Enter Transaction ID to delete", allow_cancel=True)
        if tx_id_str is None:
            return

        try:
            tx_id = int(tx_id_str)
        except ValueError:
            print_error("Transaction ID must be an integer.")
            pause()
            return

        u_id = self.current_user.user_id
        tx = self.income.get_income_by_id(u_id, tx_id)
        is_income = True
        if not tx:
            tx = self.expenses.get_expense_by_id(u_id, tx_id)
            is_income = False

        if not tx:
            print_error(f"Transaction ID #{tx_id} not found in your records.")
            pause()
            return

        print(f"\nTransaction Details:")
        print(f"  Type:        {tx['transaction_type']}")
        print(f"  Date:        {tx['transaction_date']}")
        print(f"  Category:    {tx['category_name']}")
        print(f"  Amount:      {format_currency(tx['amount'])}")
        print(f"  Description: {tx['description'] or '-'}")

        confirm = get_input("\nAre you sure you want to delete this record? (yes/no)", default="no")
        if confirm.lower() not in ("yes", "y"):
            print("\nDeletion cancelled.")
            pause()
            return

        if is_income:
            ok, msg = self.income.delete_income(u_id, tx_id)
        else:
            ok, msg = self.expenses.delete_expense(u_id, tx_id)

        if ok:
            print_success(msg)
        else:
            print_error(msg)
        pause()

    # ---------------------------------------------------------
    # 6. CATEGORY MANAGEMENT
    # ---------------------------------------------------------

    def handle_manage_categories(self):
        """Category management menu."""
        while True:
            print_header("CATEGORY MANAGEMENT")
            print("1. View All Categories")
            print("2. Add Custom Category")
            print("3. Delete Custom Category")
            print("0. Back to Main Dashboard")

            choice = get_input("\nEnter your choice")
            if choice == "1":
                self._display_categories_table()
                pause()
            elif choice == "2":
                self._add_custom_category()
            elif choice == "3":
                self._delete_custom_category()
            elif choice == "0":
                break
            else:
                print_error("Invalid selection.")
                pause()

    def _display_categories_table(self):
        """Displays system and custom categories."""
        cats = self.categories.get_categories(self.current_user.user_id)
        headers = ["ID", "Category Name", "Type", "Ownership"]
        rows = [
            [c["category_id"], c["category_name"], c["category_type"], c["ownership"]]
            for c in cats
        ]
        print_table(headers, rows, alignments=["R", "L", "L", "L"])

    def _add_custom_category(self):
        """Prompt user to create a new custom category."""
        print_header("ADD CUSTOM CATEGORY")
        print("Select Type:")
        print("  1. Expense Category")
        print("  2. Income Category")
        type_choice = get_input("Choice (1-2)", allow_cancel=True)
        if type_choice is None:
            return

        cat_type = "EXPENSE" if type_choice == "1" else ("INCOME" if type_choice == "2" else None)
        if not cat_type:
            print_error("Invalid type choice.")
            pause()
            return

        name = get_input("Enter category name", allow_cancel=True)
        if name is None:
            return

        ok, msg, _ = self.categories.add_category(self.current_user.user_id, name, cat_type)
        if ok:
            print_success(msg)
        else:
            print_error(msg)
        pause()

    def _delete_custom_category(self):
        """Delete custom category owned by the user."""
        print_header("DELETE CUSTOM CATEGORY")
        self._display_categories_table()
        cat_id_str = get_input("\nEnter Category ID to delete", allow_cancel=True)
        if cat_id_str is None:
            return

        try:
            cat_id = int(cat_id_str)
        except ValueError:
            print_error("Category ID must be an integer.")
            pause()
            return

        ok, msg = self.categories.delete_category(self.current_user.user_id, cat_id)
        if ok:
            print_success(msg)
        else:
            print_error(msg)
        pause()

    # ---------------------------------------------------------
    # 7. BUDGET MANAGEMENT
    # ---------------------------------------------------------

    def handle_manage_budget(self):
        """Budget management menu."""
        while True:
            print_header("MONTHLY BUDGET MANAGEMENT")
            print("1. View Current Month Budget Status")
            print("2. Set or Update Monthly Budget")
            print("3. View All Budgets History")
            print("4. Delete a Monthly Budget")
            print("0. Back to Main Dashboard")

            choice = get_input("\nEnter your choice")
            if choice == "1":
                self._view_current_month_budget()
                pause()
            elif choice == "2":
                self._set_or_update_budget()
            elif choice == "3":
                self._view_all_budgets()
                pause()
            elif choice == "4":
                self._delete_budget()
            elif choice == "0":
                break
            else:
                print_error("Invalid selection.")
                pause()

    def _view_current_month_budget(self):
        """Display budget and expenditure for the current month."""
        now = datetime.now()
        b_info = self.budget.get_budget(self.current_user.user_id, now.month, now.year)

        print_header(f"BUDGET STATUS: {now.strftime('%B %Y')}")
        if not b_info:
            print_alert(f"No monthly budget set for {now.strftime('%B %Y')}.")
            print("Tip: Use option 2 to set a budget for this month.")
            return

        headers = ["Metric", "Amount / Value"]
        rows = [
            ["Monthly Budget", format_currency(b_info["budget_amount"])],
            ["Total Spent", format_currency(b_info["total_spent"])],
            ["Remaining Budget", format_currency(b_info["remaining"])],
            ["Utilization %", f"{b_info['percent_used']:.2f}%"],
            ["Status", b_info["status"]],
        ]
        print_table(headers, rows, alignments=["L", "R"])
        print("\n" + b_info["status_message"])

    def _set_or_update_budget(self):
        """Set or update budget for chosen month/year."""
        print_header("SET / UPDATE MONTHLY BUDGET")
        now = datetime.now()

        m_str = get_input("Enter Month (1-12)", default=str(now.month), allow_cancel=True)
        if m_str is None:
            return
        try:
            month = int(m_str)
        except ValueError:
            print_error("Month must be an integer between 1 and 12.")
            pause()
            return

        y_str = get_input("Enter Year (e.g. 2026)", default=str(now.year), allow_cancel=True)
        if y_str is None:
            return
        try:
            year = int(y_str)
        except ValueError:
            print_error("Year must be a valid 4-digit integer.")
            pause()
            return

        amt_str = get_input("Enter Monthly Budget Amount in Rupees", allow_cancel=True)
        if amt_str is None:
            return
        valid_amt, amt_paise, amt_err = parse_amount_to_paise(amt_str)
        if not valid_amt:
            print_error(amt_err)
            pause()
            return

        ok, msg, _ = self.budget.set_or_update_budget(
            self.current_user.user_id, month, year, amt_paise
        )
        if ok:
            print_success(msg)
            # Immediately show status
            b_info = self.budget.get_budget(self.current_user.user_id, month, year)
            if b_info:
                print(b_info["status_message"])
        else:
            print_error(msg)
        pause()

    def _view_all_budgets(self):
        """List all configured budgets with utilization status."""
        budgets = self.budget.get_all_budgets(self.current_user.user_id)
        print_header("ALL CONFIGURED BUDGETS")
        headers = ["ID", "Month/Year", "Budget", "Spent", "Remaining", "Used %", "Status"]
        rows = []
        for b in budgets:
            rows.append(
                [
                    b["budget_id"],
                    f"{b['month']:02d}/{b['year']}",
                    format_currency(b["budget_amount"]),
                    format_currency(b["total_spent"]),
                    format_currency(b["remaining"]),
                    f"{b['percent_used']:.1f}%",
                    b["status"],
                ]
            )
        print_table(headers, rows, alignments=["R", "L", "R", "R", "R", "R", "L"])

    def _delete_budget(self):
        """Delete a configured budget."""
        print_header("DELETE MONTHLY BUDGET")
        self._view_all_budgets()
        b_id_str = get_input("\nEnter Budget ID to delete", allow_cancel=True)
        if b_id_str is None:
            return

        try:
            b_id = int(b_id_str)
        except ValueError:
            print_error("Budget ID must be an integer.")
            pause()
            return

        ok, msg = self.budget.delete_budget(self.current_user.user_id, b_id)
        if ok:
            print_success(msg)
        else:
            print_error(msg)
        pause()

    # ---------------------------------------------------------
    # 8. FINANCIAL SUMMARY / DASHBOARD
    # ---------------------------------------------------------

    def handle_financial_summary(self):
        """Displays total income, expenses, balance, monthly savings, and spending summary."""
        now = datetime.now()
        data = self.dashboard.get_financial_summary(
            self.current_user.user_id, now.month, now.year
        )

        print_header("FINANCIAL DASHBOARD SUMMARY", f"As of {now.strftime('%d-%b-%Y')}")

        # High level overview
        overview_headers = ["Financial Metric", "Amount (INR)"]
        overview_rows = [
            ["Lifetime Total Income", format_currency(data["total_income"])],
            ["Lifetime Total Expenses", format_currency(data["total_expenses"])],
            ["Net Balance (Income - Expenses)", format_currency(data["balance"])],
            ["Current Month Income", format_currency(data["month_income"])],
            ["Current Month Expenses", format_currency(data["month_expenses"])],
            ["Current Month Savings", format_currency(data["monthly_savings"])],
        ]
        print_table(overview_headers, overview_rows, alignments=["L", "R"])

        # Highest and Lowest Expenses
        print("\n" + "-" * 60)
        print("NOTABLE EXPENSES:".center(60))
        print("-" * 60)
        if data["highest_expense"]:
            h = data["highest_expense"]
            print(
                f"[▲] Highest Expense: {format_currency(h['amount'])} "
                f"({h['category_name']} on {format_date(h['transaction_date'])}) - '{h['description'] or 'No description'}'"
            )
        else:
            print("[▲] Highest Expense: None recorded.")

        if data["lowest_expense"]:
            l = data["lowest_expense"]
            print(
                f"[▼] Lowest Expense:  {format_currency(l['amount'])} "
                f"({l['category_name']} on {format_date(l['transaction_date'])}) - '{l['description'] or 'No description'}'"
            )
        else:
            print("[▼] Lowest Expense:  None recorded.")

        # Category-wise breakdown
        print("\n" + "-" * 60)
        print("CATEGORY-WISE SPENDING BREAKDOWN:".center(60))
        print("-" * 60)
        cat_headers = ["Category", "Total Spent", "Count", "% of Total"]
        cat_rows = []
        for c in data["category_breakdown"]:
            cat_rows.append(
                [
                    c["category_name"],
                    format_currency(c["amount"]),
                    c["count"],
                    f"{c['percentage']:.2f}%",
                ]
            )
        print_table(cat_headers, cat_rows, alignments=["L", "R", "R", "R"])
        pause()

    # ---------------------------------------------------------
    # 9. REPORTS & CSV EXPORT
    # ---------------------------------------------------------

    def handle_reports_menu(self):
        """Submenu for generating various analytical financial reports."""
        while True:
            print_header("FINANCIAL REPORTS")
            print("1. Daily Report")
            print("2. Weekly Report")
            print("3. Monthly Report")
            print("4. Yearly Report")
            print("5. Category-wise Expense Report")
            print("6. Income vs Expense Comparative Report")
            print("0. Back to Main Dashboard")

            choice = get_input("\nEnter your choice")
            if choice == "1":
                self._report_daily()
            elif choice == "2":
                self._report_weekly()
            elif choice == "3":
                self._report_monthly()
            elif choice == "4":
                self._report_yearly()
            elif choice == "5":
                self._report_category_wise()
            elif choice == "6":
                self._report_income_vs_expense()
            elif choice == "0":
                break
            else:
                print_error("Invalid selection.")
                pause()

    def _report_daily(self):
        """Daily transactions and totals."""
        print_header("DAILY FINANCIAL REPORT")
        today_str = datetime.now().strftime("%Y-%m-%d")
        d_str = get_input("Enter Date [YYYY-MM-DD]", default=today_str, allow_cancel=True)
        if d_str is None:
            return
        valid_d, clean_d, err_d = validate_date(d_str)
        if not valid_d:
            print_error(err_d)
            pause()
            return

        rep = self.reports.get_daily_report(self.current_user.user_id, clean_d)
        print(f"\nReport for {format_date(clean_d)}:")
        headers = ["ID", "Type", "Category", "Amount", "Description"]
        rows = [
            [
                r["transaction_id"],
                r["transaction_type"],
                r["category_name"],
                format_currency(r["amount"]),
                r["description"] or "-",
            ]
            for r in rep["transactions"]
        ]
        print_table(headers, rows, alignments=["R", "L", "L", "R", "L"])

        print(f"\n  Daily Income:   {format_currency(rep['total_income'])}")
        print(f"  Daily Expenses: {format_currency(rep['total_expenses'])}")
        print(f"  Net Cash Flow:  {format_currency(rep['net_balance'])}")
        pause()

    def _report_weekly(self):
        """Weekly report for 7-day period."""
        print_header("WEEKLY FINANCIAL REPORT")
        today_str = datetime.now().strftime("%Y-%m-%d")
        end_str = get_input("Enter End Date [YYYY-MM-DD]", default=today_str, allow_cancel=True)
        if end_str is None:
            return
        valid_e, clean_e, err_e = validate_date(end_str)
        if not valid_e:
            print_error(err_e)
            pause()
            return

        rep = self.reports.get_weekly_report(self.current_user.user_id, clean_e)
        print(f"\nWeekly Period: {format_date(rep['start_date'])} to {format_date(rep['end_date'])}")

        headers = ["Date", "Income", "Expense", "Daily Net"]
        rows = []
        for d_str, vals in rep["daily_breakdown"].items():
            inc = vals["INCOME"]
            exp = vals["EXPENSE"]
            net = inc - exp
            rows.append(
                [
                    format_date(d_str),
                    format_currency(inc),
                    format_currency(exp),
                    format_currency(net),
                ]
            )
        print_table(headers, rows, alignments=["L", "R", "R", "R"])

        print(f"\n  7-Day Total Income:   {format_currency(rep['total_income'])}")
        print(f"  7-Day Total Expenses: {format_currency(rep['total_expenses'])}")
        print(f"  7-Day Net Savings:    {format_currency(rep['net_savings'])}")
        pause()

    def _report_monthly(self):
        """Monthly detailed report."""
        print_header("MONTHLY FINANCIAL REPORT")
        now = datetime.now()
        m_str = get_input("Enter Month (1-12)", default=str(now.month), allow_cancel=True)
        if m_str is None:
            return
        try:
            m = int(m_str)
        except ValueError:
            print_error("Invalid month.")
            pause()
            return

        y_str = get_input("Enter Year", default=str(now.year), allow_cancel=True)
        if y_str is None:
            return
        try:
            y = int(y_str)
        except ValueError:
            print_error("Invalid year.")
            pause()
            return

        rep = self.reports.get_monthly_report(self.current_user.user_id, m, y)
        print_header(f"MONTHLY STATEMENT: {datetime(y, m, 1).strftime('%B %Y')}")

        print(f"  Monthly Income:     {format_currency(rep['total_income'])}")
        print(f"  Monthly Expenses:   {format_currency(rep['total_expenses'])}")
        print(f"  Monthly Net Savings:{format_currency(rep['net_savings'])}")
        if rep["budget_amount"]:
            pct = (rep["total_expenses"] / rep["budget_amount"] * 100.0)
            print(f"  Monthly Budget:     {format_currency(rep['budget_amount'])} ({pct:.1f}% used)")

        print("\nCategory-wise Expense Distribution:")
        cat_headers = ["Category", "Total Spent", "Count"]
        cat_rows = [
            [r["category_name"], format_currency(r["total"]), r["count"]]
            for r in rep["category_breakdown"]
        ]
        print_table(cat_headers, cat_rows, alignments=["L", "R", "R"])
        pause()

    def _report_yearly(self):
        """Yearly month-by-month financial summary."""
        print_header("YEARLY FINANCIAL REPORT")
        now = datetime.now()
        y_str = get_input("Enter Year", default=str(now.year), allow_cancel=True)
        if y_str is None:
            return
        try:
            year = int(y_str)
        except ValueError:
            print_error("Invalid year.")
            pause()
            return

        rep = self.reports.get_yearly_report(self.current_user.user_id, year)
        print_header(f"ANNUAL FINANCIAL STATEMENT - {year}")

        month_names = [
            "", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
            "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
        ]
        headers = ["Month", "Income", "Expense", "Net Savings"]
        rows = []
        for m, data in rep["monthly_data"].items():
            rows.append(
                [
                    month_names[m],
                    format_currency(data["INCOME"]),
                    format_currency(data["EXPENSE"]),
                    format_currency(data["SAVINGS"]),
                ]
            )
        print_table(headers, rows, alignments=["L", "R", "R", "R"])

        print(f"\n  Annual Total Income:   {format_currency(rep['total_income'])}")
        print(f"  Annual Total Expenses: {format_currency(rep['total_expenses'])}")
        print(f"  Annual Net Savings:    {format_currency(rep['net_savings'])}")
        pause()

    def _report_category_wise(self):
        """Category-wise distribution report."""
        print_header("CATEGORY-WISE EXPENSE REPORT")
        results = self.reports.get_category_wise_report(
            self.current_user.user_id, transaction_type="EXPENSE"
        )
        headers = ["Category", "Count", "Total Amount", "% of Total"]
        rows = [
            [
                r["category"],
                r["count"],
                format_currency(r["total_amount"]),
                f"{r['percentage']:.2f}%",
            ]
            for r in results
        ]
        print_table(headers, rows, alignments=["L", "R", "R", "R"])
        pause()

    def _report_income_vs_expense(self):
        """Income vs expense comparative report."""
        print_header("INCOME VS EXPENSE COMPARATIVE REPORT")
        rep = self.reports.get_income_vs_expense_report(self.current_user.user_id)

        headers = ["Metric", "Value"]
        rows = [
            ["Total Income Recorded", format_currency(rep["income_total"])],
            ["Income Transactions", rep["income_count"]],
            ["Total Expenses Recorded", format_currency(rep["expense_total"])],
            ["Expense Transactions", rep["expense_count"]],
            ["Net Accumulated Savings", format_currency(rep["net_savings"])],
            ["Savings Rate (%)", f"{rep['savings_rate']:.2f}%"],
        ]
        print_table(headers, rows, alignments=["L", "R"])
        pause()

    def handle_export_csv(self):
        """Export transactions to CSV file."""
        print_header("EXPORT TRANSACTIONS TO CSV")
        print("1. Export All Transactions")
        print("2. Export Income Records Only")
        print("3. Export Expense Records Only")
        print("0. Cancel")

        choice = get_input("\nEnter choice", allow_cancel=True)
        if choice in (None, "0"):
            return

        tx_type = None
        if choice == "2":
            tx_type = "INCOME"
        elif choice == "3":
            tx_type = "EXPENSE"

        ok, msg, filepath = self.reports.export_transactions_to_csv(
            self.current_user.user_id, transaction_type=tx_type
        )
        if ok and filepath:
            print_success(msg)
            print(f"File saved at: {filepath}")
        else:
            print_error(msg)
        pause()

    # ---------------------------------------------------------
    # 10. ACCOUNT SETTINGS
    # ---------------------------------------------------------

    def handle_change_password(self):
        """Change user password."""
        print_header("CHANGE PASSWORD")
        old_pwd = get_input("Enter current password", allow_cancel=True)
        if old_pwd is None:
            return

        new_pwd = get_input("Enter new password (min 6 chars)", allow_cancel=True)
        if new_pwd is None:
            return

        confirm_pwd = get_input("Confirm new password", allow_cancel=True)
        if confirm_pwd is None:
            return

        if new_pwd != confirm_pwd:
            print_error("New passwords do not match.")
            pause()
            return

        ok, msg = self.auth.change_password(self.current_user.user_id, old_pwd, new_pwd)
        if ok:
            print_success(msg)
        else:
            print_error(msg)
        pause()


def main():
    """Application entry point."""
    app = ExpenseTrackerApp()
    app.run()


if __name__ == "__main__":
    main()
