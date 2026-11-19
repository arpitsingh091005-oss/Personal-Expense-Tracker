"""
Dashboard Feature Service.
Computes and prepares real-time financial metrics:
Total Income, Total Expenses, Balance, Monthly Savings, Highest/Lowest Expenses,
and Category-wise Spending Summaries.
"""

from datetime import datetime
from database import DatabaseManager, db


class DashboardService:
    """Provides high-level financial aggregations, statistics, and balances."""

    def __init__(self, db_manager: DatabaseManager = db):
        self.db = db_manager

    def get_financial_summary(
        self, user_id: int, month: int | None = None, year: int | None = None
    ) -> dict:
        """
        Compute comprehensive financial metrics for a user.
        If month and year are not specified, defaults to the current month.
        """
        now = datetime.now()
        target_month = month if month is not None else now.month
        target_year = year if year is not None else now.year

        # 1. Lifetime Total Income
        inc_row = self.db.fetch_one(
            """
            SELECT COALESCE(SUM(amount), 0) as total_income
            FROM transactions
            WHERE user_id = ? AND transaction_type = 'INCOME';
            """,
            (user_id,),
        )
        total_income = inc_row["total_income"] if inc_row else 0

        # 2. Lifetime Total Expenses
        exp_row = self.db.fetch_one(
            """
            SELECT COALESCE(SUM(amount), 0) as total_expenses
            FROM transactions
            WHERE user_id = ? AND transaction_type = 'EXPENSE';
            """,
            (user_id,),
        )
        total_expenses = exp_row["total_expenses"] if exp_row else 0

        # 3. Overall Balance
        balance = total_income - total_expenses

        # 4. Monthly figures for target month
        month_prefix = f"{target_year:04d}-{target_month:02d}%"
        m_inc_row = self.db.fetch_one(
            """
            SELECT COALESCE(SUM(amount), 0) as month_income
            FROM transactions
            WHERE user_id = ? AND transaction_type = 'INCOME'
              AND transaction_date LIKE ?;
            """,
            (user_id, month_prefix),
        )
        month_income = m_inc_row["month_income"] if m_inc_row else 0

        m_exp_row = self.db.fetch_one(
            """
            SELECT COALESCE(SUM(amount), 0) as month_expenses
            FROM transactions
            WHERE user_id = ? AND transaction_type = 'EXPENSE'
              AND transaction_date LIKE ?;
            """,
            (user_id, month_prefix),
        )
        month_expenses = m_exp_row["month_expenses"] if m_exp_row else 0

        monthly_savings = month_income - month_expenses

        # 5. Highest Expense
        highest_exp = self.db.fetch_one(
            """
            SELECT t.amount, t.description, t.transaction_date, c.category_name
            FROM transactions t
            JOIN categories c ON t.category_id = c.category_id
            WHERE t.user_id = ? AND t.transaction_type = 'EXPENSE'
            ORDER BY t.amount DESC, t.transaction_date DESC
            LIMIT 1;
            """,
            (user_id,),
        )

        # 6. Lowest Expense
        lowest_exp = self.db.fetch_one(
            """
            SELECT t.amount, t.description, t.transaction_date, c.category_name
            FROM transactions t
            JOIN categories c ON t.category_id = c.category_id
            WHERE t.user_id = ? AND t.transaction_type = 'EXPENSE'
            ORDER BY t.amount ASC, t.transaction_date DESC
            LIMIT 1;
            """,
            (user_id,),
        )

        # 7. Category-wise Spending Summary (Lifetime and Monthly)
        cat_summary_rows = self.db.fetch_all(
            """
            SELECT c.category_name, COALESCE(SUM(t.amount), 0) as category_total,
                   COUNT(t.transaction_id) as transaction_count
            FROM categories c
            JOIN transactions t ON c.category_id = t.category_id
            WHERE t.user_id = ? AND t.transaction_type = 'EXPENSE'
            GROUP BY c.category_id
            ORDER BY category_total DESC;
            """,
            (user_id,),
        )

        category_breakdown = []
        for row in cat_summary_rows:
            cat_total = row["category_total"]
            percentage = (cat_total / total_expenses * 100.0) if total_expenses > 0 else 0.0
            category_breakdown.append(
                {
                    "category_name": row["category_name"],
                    "amount": cat_total,
                    "count": row["transaction_count"],
                    "percentage": percentage,
                }
            )

        return {
            "total_income": total_income,
            "total_expenses": total_expenses,
            "balance": balance,
            "target_month": target_month,
            "target_year": target_year,
            "month_income": month_income,
            "month_expenses": month_expenses,
            "monthly_savings": monthly_savings,
            "highest_expense": highest_exp,
            "lowest_expense": lowest_exp,
            "category_breakdown": category_breakdown,
        }
