"""
Expense Feature Service.
Handles recording, updating, deleting, viewing, filtering, and searching expense records.
Integrates real-time monthly budget monitoring and warning alerts.
"""

import sqlite3
from datetime import datetime
from database import DatabaseManager, db
from utils.validators import validate_date
from utils.helpers import format_currency


class ExpenseService:
    """Provides complete CRUD, filtering, and search operations for user expenses."""

    def __init__(self, db_manager: DatabaseManager = db):
        self.db = db_manager

    def check_budget_status(
        self, user_id: int, month: int, year: int
    ) -> dict | None:
        """
        Check current month's budget vs total expenses.
        Returns a dict with budget metrics or None if no budget set.
        """
        budget_row = self.db.fetch_one(
            """
            SELECT budget_amount FROM budgets
            WHERE user_id = ? AND month = ? AND year = ?;
            """,
            (user_id, month, year),
        )
        if not budget_row:
            return None

        budget_amount = budget_row["budget_amount"]

        month_str = f"{year:04d}-{month:02d}%"
        spent_row = self.db.fetch_one(
            """
            SELECT COALESCE(SUM(amount), 0) as total_spent
            FROM transactions
            WHERE user_id = ? AND transaction_type = 'EXPENSE'
              AND transaction_date LIKE ?;
            """,
            (user_id, month_str),
        )
        total_spent = spent_row["total_spent"] if spent_row else 0
        remaining = budget_amount - total_spent
        percent_used = (total_spent / budget_amount) * 100.0 if budget_amount > 0 else 0.0

        warning = None
        if total_spent > budget_amount:
            overspent = total_spent - budget_amount
            warning = (
                f"[ALERT] BUDGET EXCEEDED! You have spent {format_currency(total_spent)}, "
                f"exceeding your monthly budget of {format_currency(budget_amount)} "
                f"by {format_currency(overspent)} ({percent_used:.1f}% used)."
            )
        elif percent_used >= 80.0:
            warning = (
                f"[WARNING] 80% BUDGET THRESHOLD REACHED! You have spent "
                f"{format_currency(total_spent)} of your {format_currency(budget_amount)} budget "
                f"({percent_used:.1f}% used). Remaining: {format_currency(remaining)}."
            )

        return {
            "budget_amount": budget_amount,
            "total_spent": total_spent,
            "remaining": remaining,
            "percent_used": percent_used,
            "warning": warning,
        }

    def add_expense(
        self,
        user_id: int,
        category_id: int,
        amount_paise: int,
        transaction_date: str,
        description: str = "",
    ) -> tuple[bool, str, int | None, str | None]:
        """
        Record a new expense entry.
        Returns (success, message, transaction_id, budget_warning).
        """
        if amount_paise <= 0:
            return False, "Expense amount must be greater than zero.", None, None

        d_valid, clean_date, d_err = validate_date(transaction_date)
        if not d_valid:
            return False, d_err, None, None

        cat = self.db.fetch_one(
            """
            SELECT category_id, category_name, category_type
            FROM categories
            WHERE category_id = ? AND category_type = 'EXPENSE'
              AND (user_id IS NULL OR user_id = ?);
            """,
            (category_id, user_id),
        )
        if not cat:
            return (
                False,
                "Selected category is not a valid expense category.",
                None,
                None,
            )

        clean_desc = description.strip() if description else ""

        try:
            tx_id = self.db.execute(
                """
                INSERT INTO transactions (
                    user_id, category_id, amount, transaction_type, description, transaction_date
                )
                VALUES (?, ?, ?, 'EXPENSE', ?, ?);
                """,
                (user_id, category_id, amount_paise, clean_desc, clean_date),
            )

            dt = datetime.strptime(clean_date, "%Y-%m-%d")
            budget_info = self.check_budget_status(user_id, dt.month, dt.year)
            warning = budget_info["warning"] if budget_info else None

            return True, "Expense recorded successfully!", tx_id, warning
        except Exception as e:
            return False, f"Database error while saving expense: {str(e)}", None, None

    def get_expenses(
        self,
        user_id: int,
        start_date: str | None = None,
        end_date: str | None = None,
        category_id: int | None = None,
        search_term: str | None = None,
    ) -> list[sqlite3.Row]:
        """
        Retrieve expense records for the user with optional filters by date range,
        category, and search term.
        """
        query = """
            SELECT t.transaction_id, t.user_id, t.category_id, t.amount,
                   t.transaction_type, t.description, t.transaction_date, t.created_at,
                   c.category_name
            FROM transactions t
            JOIN categories c ON t.category_id = c.category_id
            WHERE t.user_id = ? AND t.transaction_type = 'EXPENSE'
        """
        params: list = [user_id]

        if start_date:
            query += " AND t.transaction_date >= ?"
            params.append(start_date)

        if end_date:
            query += " AND t.transaction_date <= ?"
            params.append(end_date)

        if category_id:
            query += " AND t.category_id = ?"
            params.append(category_id)

        if search_term and search_term.strip():
            query += " AND (t.description LIKE ? OR c.category_name LIKE ?)"
            term = f"%{search_term.strip()}%"
            params.extend([term, term])

        query += " ORDER BY t.transaction_date DESC, t.transaction_id DESC;"
        return self.db.fetch_all(query, tuple(params))

    def get_expense_by_id(
        self, user_id: int, transaction_id: int
    ) -> sqlite3.Row | None:
        """Fetch a single expense record ensuring strict user isolation."""
        query = """
            SELECT t.transaction_id, t.user_id, t.category_id, t.amount,
                   t.transaction_type, t.description, t.transaction_date,
                   c.category_name
            FROM transactions t
            JOIN categories c ON t.category_id = c.category_id
            WHERE t.transaction_id = ? AND t.user_id = ? AND t.transaction_type = 'EXPENSE';
        """
        return self.db.fetch_one(query, (transaction_id, user_id))

    def update_expense(
        self,
        user_id: int,
        transaction_id: int,
        category_id: int,
        amount_paise: int,
        transaction_date: str,
        description: str = "",
    ) -> tuple[bool, str, str | None]:
        """
        Update an existing expense record.
        Returns (success, message, optional_budget_warning).
        """
        existing = self.get_expense_by_id(user_id, transaction_id)
        if not existing:
            return False, "Expense record not found or access denied.", None

        if amount_paise <= 0:
            return False, "Expense amount must be greater than zero.", None

        d_valid, clean_date, d_err = validate_date(transaction_date)
        if not d_valid:
            return False, d_err, None

        cat = self.db.fetch_one(
            """
            SELECT category_id FROM categories
            WHERE category_id = ? AND category_type = 'EXPENSE'
              AND (user_id IS NULL OR user_id = ?);
            """,
            (category_id, user_id),
        )
        if not cat:
            return False, "Selected category is not a valid expense category.", None

        clean_desc = description.strip() if description else ""

        try:
            self.db.execute_non_query(
                """
                UPDATE transactions
                SET category_id = ?, amount = ?, transaction_date = ?, description = ?
                WHERE transaction_id = ? AND user_id = ? AND transaction_type = 'EXPENSE';
                """,
                (category_id, amount_paise, clean_date, clean_desc, transaction_id, user_id),
            )

            dt = datetime.strptime(clean_date, "%Y-%m-%d")
            budget_info = self.check_budget_status(user_id, dt.month, dt.year)
            warning = budget_info["warning"] if budget_info else None

            return True, "Expense record updated successfully!", warning
        except Exception as e:
            return False, f"Database error updating expense: {str(e)}", None

    def delete_expense(self, user_id: int, transaction_id: int) -> tuple[bool, str]:
        """Delete an expense record after verifying user ownership."""
        existing = self.get_expense_by_id(user_id, transaction_id)
        if not existing:
            return False, "Expense record not found or access denied."

        try:
            self.db.execute_non_query(
                "DELETE FROM transactions WHERE transaction_id = ? AND user_id = ?;",
                (transaction_id, user_id),
            )
            return True, "Expense record deleted successfully!"
        except Exception as e:
            return False, f"Database error deleting expense: {str(e)}"
