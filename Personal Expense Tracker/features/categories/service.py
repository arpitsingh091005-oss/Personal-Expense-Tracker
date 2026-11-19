"""
Category Feature Service.
Handles system default categories and user-defined custom categories
for both income and expense transaction types.
"""

import sqlite3
from database import DatabaseManager, db


class CategoryService:
    """Provides category retrieval, creation, and deletion functionality."""

    def __init__(self, db_manager: DatabaseManager = db):
        self.db = db_manager

    def get_categories(
        self, user_id: int, category_type: str | None = None
    ) -> list[sqlite3.Row]:
        """
        Get all accessible categories for a user:
        Combines global system categories (user_id IS NULL) and the user's custom categories.
        """
        query = """
            SELECT category_id, user_id, category_name, category_type,
                   CASE WHEN user_id IS NULL THEN 'System' ELSE 'Custom' END as ownership
            FROM categories
            WHERE (user_id IS NULL OR user_id = ?)
        """
        params: list = [user_id]

        if category_type:
            query += " AND category_type = ?"
            params.append(category_type.upper())

        query += " ORDER BY category_type ASC, ownership DESC, category_name ASC;"
        return self.db.fetch_all(query, tuple(params))

    def get_category_by_id(
        self, category_id: int, user_id: int
    ) -> sqlite3.Row | None:
        """Fetch a category if it is accessible to the specified user."""
        query = """
            SELECT category_id, user_id, category_name, category_type
            FROM categories
            WHERE category_id = ? AND (user_id IS NULL OR user_id = ?);
        """
        return self.db.fetch_one(query, (category_id, user_id))

    def get_category_by_name(
        self, category_name: str, category_type: str, user_id: int
    ) -> sqlite3.Row | None:
        """Find category by case-insensitive name, type, and accessibility."""
        query = """
            SELECT category_id, user_id, category_name, category_type
            FROM categories
            WHERE LOWER(category_name) = LOWER(?)
              AND category_type = ?
              AND (user_id IS NULL OR user_id = ?);
        """
        return self.db.fetch_one(
            query, (category_name.strip(), category_type.upper(), user_id)
        )

    def add_category(
        self, user_id: int, category_name: str, category_type: str
    ) -> tuple[bool, str, int | None]:
        """
        Add a new user-defined custom category.
        Validates name, type, and uniqueness for the user.
        """
        if not category_name or not category_name.strip():
            return False, "Category name cannot be empty.", None

        category_name = category_name.strip()
        category_type = category_type.upper().strip()

        if category_type not in ("INCOME", "EXPENSE"):
            return False, "Category type must be either 'INCOME' or 'EXPENSE'.", None

        existing = self.get_category_by_name(category_name, category_type, user_id)
        if existing:
            return (
                False,
                f"A {category_type.lower()} category named '{category_name}' already exists.",
                None,
            )

        try:
            cat_id = self.db.execute(
                """
                INSERT INTO categories (user_id, category_name, category_type)
                VALUES (?, ?, ?);
                """,
                (user_id, category_name, category_type),
            )
            return True, f"Category '{category_name}' created successfully!", cat_id
        except sqlite3.IntegrityError:
            return False, f"Category '{category_name}' already exists.", None
        except Exception as e:
            return False, f"Database error: {str(e)}", None

    def delete_category(self, user_id: int, category_id: int) -> tuple[bool, str]:
        """
        Delete a custom category owned by the user.
        Prevents deletion of system default categories and categories with linked transactions.
        """
        category = self.db.fetch_one(
            "SELECT category_id, user_id, category_name FROM categories WHERE category_id = ?;",
            (category_id,),
        )
        if not category:
            return False, "Category not found."

        if category["user_id"] is None:
            return False, "System default categories cannot be deleted."

        if category["user_id"] != user_id:
            return False, "Access denied. You do not own this category."

        usage = self.db.fetch_one(
            "SELECT COUNT(*) as count FROM transactions WHERE category_id = ?;",
            (category_id,),
        )
        if usage and usage["count"] > 0:
            return (
                False,
                f"Cannot delete category '{category['category_name']}' because it is linked to "
                f"{usage['count']} transaction(s). Reassign or delete those transactions first.",
            )

        self.db.execute_non_query(
            "DELETE FROM categories WHERE category_id = ? AND user_id = ?;",
            (category_id, user_id),
        )
        return True, f"Category '{category['category_name']}' deleted successfully!"
