"""
Income Feature Service.
Handles recording, updating, deleting, viewing, and searching income records.
"""

import sqlite3
from database import DatabaseManager, db
from utils.validators import validate_date


class IncomeService:
    """Provides complete CRUD and search operations for user income records."""

    def __init__(self, db_manager: DatabaseManager = db):
        self.db = db_manager

    def add_income(
        self,
        user_id: int,
        category_id: int,
        amount_paise: int,
        transaction_date: str,
        description: str = "",
    ) -> tuple[bool, str, int | None]:
        """
        Record a new income entry.
        Verifies that amount is positive, date is valid, and category is an accessible income category.
        """
        if amount_paise <= 0:
            return False, "Income amount must be greater than zero.", None

        d_valid, clean_date, d_err = validate_date(transaction_date)
        if not d_valid:
            return False, d_err, None

        # Verify category exists, is accessible, and is of type INCOME
        cat = self.db.fetch_one(
            """
            SELECT category_id, category_name, category_type
            FROM categories
            WHERE category_id = ? AND category_type = 'INCOME'
              AND (user_id IS NULL OR user_id = ?);
            """,
            (category_id, user_id),
        )
        if not cat:
            return False, "Selected category is not a valid income category.", None

        clean_desc = description.strip() if description else ""

        try:
            tx_id = self.db.execute(
                """
                INSERT INTO transactions (
                    user_id, category_id, amount, transaction_type, description, transaction_date
                )
                VALUES (?, ?, ?, 'INCOME', ?, ?);
                """,
                (user_id, category_id, amount_paise, clean_desc, clean_date),
            )
            return True, "Income recorded successfully!", tx_id
        except Exception as e:
            return False, f"Database error while saving income: {str(e)}", None

    def get_incomes(
        self,
        user_id: int,
        start_date: str | None = None,
        end_date: str | None = None,
        category_id: int | None = None,
        search_term: str | None = None,
    ) -> list[sqlite3.Row]:
        """
        Retrieve income records for the user with optional filters by date range,
        category, and search term (matching description or category name).
        """
        query = """
            SELECT t.transaction_id, t.user_id, t.category_id, t.amount,
                   t.transaction_type, t.description, t.transaction_date, t.created_at,
                   c.category_name
            FROM transactions t
            JOIN categories c ON t.category_id = c.category_id
            WHERE t.user_id = ? AND t.transaction_type = 'INCOME'
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

    def get_income_by_id(self, user_id: int, transaction_id: int) -> sqlite3.Row | None:
        """Fetch a specific income record ensuring strict user isolation."""
        query = """
            SELECT t.transaction_id, t.user_id, t.category_id, t.amount,
                   t.transaction_type, t.description, t.transaction_date,
                   c.category_name
            FROM transactions t
            JOIN categories c ON t.category_id = c.category_id
            WHERE t.transaction_id = ? AND t.user_id = ? AND t.transaction_type = 'INCOME';
        """
        return self.db.fetch_one(query, (transaction_id, user_id))

    def update_income(
        self,
        user_id: int,
        transaction_id: int,
        category_id: int,
        amount_paise: int,
        transaction_date: str,
        description: str = "",
    ) -> tuple[bool, str]:
        """
        Update an existing income record.
        Ensures user ownership, category validity, and input sanity.
        """
        existing = self.get_income_by_id(user_id, transaction_id)
        if not existing:
            return False, "Income record not found or access denied."

        if amount_paise <= 0:
            return False, "Amount must be greater than zero."

        d_valid, clean_date, d_err = validate_date(transaction_date)
        if not d_valid:
            return False, d_err

        # Check category
        cat = self.db.fetch_one(
            """
            SELECT category_id FROM categories
            WHERE category_id = ? AND category_type = 'INCOME'
              AND (user_id IS NULL OR user_id = ?);
            """,
            (category_id, user_id),
        )
        if not cat:
            return False, "Selected category is not a valid income category."

        clean_desc = description.strip() if description else ""

        try:
            self.db.execute_non_query(
                """
                UPDATE transactions
                SET category_id = ?, amount = ?, transaction_date = ?, description = ?
                WHERE transaction_id = ? AND user_id = ? AND transaction_type = 'INCOME';
                """,
                (category_id, amount_paise, clean_date, clean_desc, transaction_id, user_id),
            )
            return True, "Income record updated successfully!"
        except Exception as e:
            return False, f"Database error updating income: {str(e)}"

    def delete_income(self, user_id: int, transaction_id: int) -> tuple[bool, str]:
        """Delete an income record after verifying user ownership."""
        existing = self.get_income_by_id(user_id, transaction_id)
        if not existing:
            return False, "Income record not found or access denied."

        try:
            self.db.execute_non_query(
                "DELETE FROM transactions WHERE transaction_id = ? AND user_id = ?;",
                (transaction_id, user_id),
            )
            return True, "Income record deleted successfully!"
        except Exception as e:
            return False, f"Database error deleting income: {str(e)}"
