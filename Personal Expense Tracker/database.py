"""
Database Management Module.
Handles SQLite3 database initialization, table creation, foreign keys,
transactions, and parameterized query execution.
"""

import sqlite3
from pathlib import Path
from contextlib import contextmanager
from config import (
    DEFAULT_DB_PATH,
    DEFAULT_INCOME_CATEGORIES,
    DEFAULT_EXPENSE_CATEGORIES,
)


class DatabaseManager:
    """
    Manages SQLite database connections, schema setup, and query operations.
    Enforces foreign keys, parameterized queries, and ACID transactions.
    """

    def __init__(self, db_path: str | Path | None = None):
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        # Ensure parent directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize_database()

    def get_connection(self) -> sqlite3.Connection:
        """
        Create and return a new SQLite connection with foreign keys enabled
        and Row factory set for dictionary-like access.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    @contextmanager
    def transaction(self):
        """Context manager for atomic database transactions with auto-commit and rollback."""
        conn = self.get_connection()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def initialize_database(self):
        """Create database tables if they do not exist and seed default categories."""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            # 1. Users Table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            )

            # 2. Categories Table
            # user_id is NULL for system default categories, or points to specific user for custom categories
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS categories (
                    category_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    category_name TEXT NOT NULL,
                    category_type TEXT NOT NULL CHECK(category_type IN ('INCOME', 'EXPENSE')),
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                    UNIQUE(user_id, category_name, category_type)
                );
                """
            )

            # 3. Transactions Table
            # amount is stored in integer paise (1 Rupee = 100 paise) to prevent floating-point inaccuracies
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS transactions (
                    transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    category_id INTEGER NOT NULL,
                    amount INTEGER NOT NULL CHECK(amount > 0),
                    transaction_type TEXT NOT NULL CHECK(transaction_type IN ('INCOME', 'EXPENSE')),
                    description TEXT,
                    transaction_date TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                    FOREIGN KEY (category_id) REFERENCES categories(category_id) ON DELETE RESTRICT
                );
                """
            )

            # 4. Budgets Table
            # UNIQUE(user_id, month, year) guarantees no duplicate monthly budgets for the same user
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS budgets (
                    budget_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    month INTEGER NOT NULL CHECK(month BETWEEN 1 AND 12),
                    year INTEGER NOT NULL CHECK(year >= 2000),
                    budget_amount INTEGER NOT NULL CHECK(budget_amount > 0),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                    UNIQUE(user_id, month, year)
                );
                """
            )

            # Create indices for fast query lookups
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_trans_user_date ON transactions(user_id, transaction_date);"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_trans_user_type ON transactions(user_id, transaction_type);"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_budget_user_my ON budgets(user_id, month, year);"
            )

            # Seed default system categories (user_id = NULL)
            self._seed_default_categories(cursor)

            conn.commit()
        finally:
            conn.close()

    def _seed_default_categories(self, cursor: sqlite3.Cursor):
        """Seed default income and expense categories if they do not exist."""
        # Seed Income categories
        for cat in DEFAULT_INCOME_CATEGORIES:
            cursor.execute(
                """
                INSERT OR IGNORE INTO categories (user_id, category_name, category_type)
                VALUES (NULL, ?, 'INCOME');
                """,
                (cat,),
            )

        # Seed Expense categories
        for cat in DEFAULT_EXPENSE_CATEGORIES:
            cursor.execute(
                """
                INSERT OR IGNORE INTO categories (user_id, category_name, category_type)
                VALUES (NULL, ?, 'EXPENSE');
                """,
                (cat,),
            )

    def execute(self, query: str, params: tuple = ()) -> int:
        """Execute an INSERT/UPDATE/DELETE query and return the lastrowid or rowcount."""
        with self.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.lastrowid

    def execute_non_query(self, query: str, params: tuple = ()) -> int:
        """Execute a query and return affected row count."""
        with self.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.rowcount

    def fetch_one(self, query: str, params: tuple = ()) -> sqlite3.Row | None:
        """Execute a SELECT query and fetch a single record."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchone()
        finally:
            conn.close()

    def fetch_all(self, query: str, params: tuple = ()) -> list[sqlite3.Row]:
        """Execute a SELECT query and fetch all matching records."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()
        finally:
            conn.close()


# Default singleton instance for convenience
db = DatabaseManager()
