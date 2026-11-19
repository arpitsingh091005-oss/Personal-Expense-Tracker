"""
Budget Feature Service.
Handles setting, viewing, updating, and monitoring monthly budgets,
including spending calculations and 80%/100% threshold alert notifications.
"""

import sqlite3
from database import DatabaseManager, db
from utils.validators import validate_month_year
from utils.helpers import format_currency
from config import BUDGET_WARNING_THRESHOLD_PERCENT


class BudgetService:
    """Manages monthly user budgets, calculations, and warning thresholds."""

    def __init__(self, db_manager: DatabaseManager = db):
        self.db = db_manager

    def set_or_update_budget(
        self, user_id: int, month: int, year: int, budget_amount_paise: int
    ) -> tuple[bool, str, int | None]:
        """
        Set or update monthly budget for a specific user, month, and year.
        Uses INSERT ... ON CONFLICT(user_id, month, year) DO UPDATE to avoid duplicates.
        """
        valid_my, my_err = validate_month_year(month, year)
        if not valid_my:
            return False, my_err, None

        if budget_amount_paise <= 0:
            return False, "Budget amount must be strictly greater than zero.", None

        try:
            existing = self.db.fetch_one(
                "SELECT budget_id FROM budgets WHERE user_id = ? AND month = ? AND year = ?;",
                (user_id, month, year),
            )

            with self.db.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO budgets (user_id, month, year, budget_amount)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(user_id, month, year)
                    DO UPDATE SET budget_amount = excluded.budget_amount;
                    """,
                    (user_id, month, year, budget_amount_paise),
                )
                b_id = existing["budget_id"] if existing else cursor.lastrowid

            action = "updated" if existing else "created"
            return (
                True,
                f"Monthly budget for {month:02d}/{year} successfully {action}!",
                b_id,
            )

        except Exception as e:
            return False, f"Database error while saving budget: {str(e)}", None

    def get_budget(self, user_id: int, month: int, year: int) -> dict | None:
        """
        Retrieve budget details for a user for a specific month and year,
        along with total spent, remaining balance, percentage, and warning status.
        """
        row = self.db.fetch_one(
            """
            SELECT budget_id, user_id, month, year, budget_amount, created_at
            FROM budgets
            WHERE user_id = ? AND month = ? AND year = ?;
            """,
            (user_id, month, year),
        )
        if not row:
            return None

        budget_amount = row["budget_amount"]

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

        if total_spent > budget_amount:
            status = "EXCEEDED"
            overspent = total_spent - budget_amount
            status_message = (
                f"[ALERT] EXCEEDED BUDGET: You have exceeded your budget by "
                f"{format_currency(overspent)} ({percent_used:.1f}% used)!"
            )
        elif percent_used >= BUDGET_WARNING_THRESHOLD_PERCENT:
            status = "WARNING_80"
            status_message = (
                f"[WARNING] 80% BUDGET REACHED: You have used {percent_used:.1f}% of your budget. "
                f"Remaining: {format_currency(remaining)}."
            )
        else:
            status = "NORMAL"
            status_message = f"[OK] Within budget ({percent_used:.1f}% used). Remaining: {format_currency(remaining)}."

        return {
            "budget_id": row["budget_id"],
            "user_id": user_id,
            "month": month,
            "year": year,
            "budget_amount": budget_amount,
            "total_spent": total_spent,
            "remaining": remaining,
            "percent_used": percent_used,
            "status": status,
            "status_message": status_message,
        }

    def get_all_budgets(self, user_id: int, year: int | None = None) -> list[dict]:
        """
        Retrieve all budgets for a user, optionally filtered by year.
        Returns calculated metrics for each month.
        """
        query = """
            SELECT budget_id, user_id, month, year, budget_amount
            FROM budgets
            WHERE user_id = ?
        """
        params: list = [user_id]
        if year:
            query += " AND year = ?"
            params.append(year)

        query += " ORDER BY year DESC, month DESC;"
        rows = self.db.fetch_all(query, tuple(params))

        results = []
        for r in rows:
            info = self.get_budget(user_id, r["month"], r["year"])
            if info:
                results.append(info)
        return results

    def delete_budget(self, user_id: int, budget_id: int) -> tuple[bool, str]:
        """Delete a monthly budget record ensuring user ownership."""
        b = self.db.fetch_one(
            "SELECT budget_id FROM budgets WHERE budget_id = ? AND user_id = ?;",
            (budget_id, user_id),
        )
        if not b:
            return False, "Budget record not found or access denied."

        try:
            self.db.execute_non_query(
                "DELETE FROM budgets WHERE budget_id = ? AND user_id = ?;",
                (budget_id, user_id),
            )
            return True, "Budget record deleted successfully!"
        except Exception as e:
            return False, f"Database error deleting budget: {str(e)}"
