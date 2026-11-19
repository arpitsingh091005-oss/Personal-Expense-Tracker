"""
Reports and Data Export Feature Service.
Generates Daily, Weekly, Monthly, Yearly, Category-wise, and Income-vs-Expense reports.
Exports transaction records to CSV using the standard Python csv module.
"""

import csv
from datetime import datetime, timedelta
from pathlib import Path
from config import EXPORTS_DIR
from database import DatabaseManager, db
from utils.helpers import paise_to_rupees


class ReportService:
    """Generates structured financial reports and handles CSV file exports."""

    def __init__(self, db_manager: DatabaseManager = db):
        self.db = db_manager

    def get_daily_report(self, user_id: int, report_date: str) -> dict:
        """
        Generate daily report for a specific date (YYYY-MM-DD).
        Returns transactions on that day, totals, and net balance.
        """
        rows = self.db.fetch_all(
            """
            SELECT t.transaction_id, t.transaction_date, t.transaction_type,
                   c.category_name, t.amount, t.description
            FROM transactions t
            JOIN categories c ON t.category_id = c.category_id
            WHERE t.user_id = ? AND t.transaction_date = ?
            ORDER BY t.transaction_id ASC;
            """,
            (user_id, report_date),
        )

        total_income = sum(
            r["amount"] for r in rows if r["transaction_type"] == "INCOME"
        )
        total_expenses = sum(
            r["amount"] for r in rows if r["transaction_type"] == "EXPENSE"
        )
        net_balance = total_income - total_expenses

        return {
            "date": report_date,
            "transactions": rows,
            "total_income": total_income,
            "total_expenses": total_expenses,
            "net_balance": net_balance,
        }

    def get_weekly_report(self, user_id: int, end_date: str | None = None) -> dict:
        """
        Generate weekly report for the 7-day period ending on end_date (default: today).
        """
        if not end_date:
            end_dt = datetime.now().date()
        else:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()

        start_dt = end_dt - timedelta(days=6)
        start_str = start_dt.strftime("%Y-%m-%d")
        end_str = end_dt.strftime("%Y-%m-%d")

        rows = self.db.fetch_all(
            """
            SELECT t.transaction_date, t.transaction_type,
                   COALESCE(SUM(t.amount), 0) as subtotal
            FROM transactions t
            WHERE t.user_id = ? AND t.transaction_date BETWEEN ? AND ?
            GROUP BY t.transaction_date, t.transaction_type
            ORDER BY t.transaction_date ASC;
            """,
            (user_id, start_str, end_str),
        )

        daily_map: dict[str, dict[str, int]] = {}
        curr = start_dt
        while curr <= end_dt:
            d_str = curr.strftime("%Y-%m-%d")
            daily_map[d_str] = {"INCOME": 0, "EXPENSE": 0}
            curr += timedelta(days=1)

        for r in rows:
            d = r["transaction_date"]
            if d in daily_map:
                daily_map[d][r["transaction_type"]] = r["subtotal"]

        total_income = sum(day["INCOME"] for day in daily_map.values())
        total_expenses = sum(day["EXPENSE"] for day in daily_map.values())
        net = total_income - total_expenses

        return {
            "start_date": start_str,
            "end_date": end_str,
            "daily_breakdown": daily_map,
            "total_income": total_income,
            "total_expenses": total_expenses,
            "net_savings": net,
        }

    def get_monthly_report(self, user_id: int, month: int, year: int) -> dict:
        """
        Generate comprehensive monthly report for month/year.
        Includes totals, categories breakdown, budget comparison, and daily aggregates.
        """
        prefix = f"{year:04d}-{month:02d}%"

        transactions = self.db.fetch_all(
            """
            SELECT t.transaction_id, t.transaction_date, t.transaction_type,
                   c.category_name, t.amount, t.description
            FROM transactions t
            JOIN categories c ON t.category_id = c.category_id
            WHERE t.user_id = ? AND t.transaction_date LIKE ?
            ORDER BY t.transaction_date ASC, t.transaction_id ASC;
            """,
            (user_id, prefix),
        )

        total_income = sum(
            t["amount"] for t in transactions if t["transaction_type"] == "INCOME"
        )
        total_expenses = sum(
            t["amount"] for t in transactions if t["transaction_type"] == "EXPENSE"
        )
        net_savings = total_income - total_expenses

        cat_rows = self.db.fetch_all(
            """
            SELECT c.category_name, COALESCE(SUM(t.amount), 0) as total, COUNT(t.transaction_id) as count
            FROM transactions t
            JOIN categories c ON t.category_id = c.category_id
            WHERE t.user_id = ? AND t.transaction_type = 'EXPENSE' AND t.transaction_date LIKE ?
            GROUP BY c.category_id
            ORDER BY total DESC;
            """,
            (user_id, prefix),
        )

        budget_row = self.db.fetch_one(
            "SELECT budget_amount FROM budgets WHERE user_id = ? AND month = ? AND year = ?;",
            (user_id, month, year),
        )
        budget_amount = budget_row["budget_amount"] if budget_row else None

        return {
            "month": month,
            "year": year,
            "transactions": transactions,
            "total_income": total_income,
            "total_expenses": total_expenses,
            "net_savings": net_savings,
            "category_breakdown": cat_rows,
            "budget_amount": budget_amount,
        }

    def get_yearly_report(self, user_id: int, year: int) -> dict:
        """
        Generate annual financial summary with month-by-month figures.
        """
        year_prefix = f"{year:04d}-%"

        rows = self.db.fetch_all(
            """
            SELECT strftime('%m', t.transaction_date) as month_str,
                   t.transaction_type,
                   COALESCE(SUM(t.amount), 0) as subtotal
            FROM transactions t
            WHERE t.user_id = ? AND t.transaction_date LIKE ?
            GROUP BY month_str, t.transaction_type
            ORDER BY month_str ASC;
            """,
            (user_id, year_prefix),
        )

        monthly_data = {
            m: {"INCOME": 0, "EXPENSE": 0, "SAVINGS": 0} for m in range(1, 13)
        }
        for r in rows:
            m = int(r["month_str"])
            monthly_data[m][r["transaction_type"]] = r["subtotal"]

        for m in monthly_data:
            monthly_data[m]["SAVINGS"] = (
                monthly_data[m]["INCOME"] - monthly_data[m]["EXPENSE"]
            )

        total_income = sum(d["INCOME"] for d in monthly_data.values())
        total_expenses = sum(d["EXPENSE"] for d in monthly_data.values())
        net_savings = total_income - total_expenses

        return {
            "year": year,
            "monthly_data": monthly_data,
            "total_income": total_income,
            "total_expenses": total_expenses,
            "net_savings": net_savings,
        }

    def get_category_wise_report(
        self,
        user_id: int,
        transaction_type: str = "EXPENSE",
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[dict]:
        """
        Aggregate category-wise spending or income with percentages.
        """
        query = """
            SELECT c.category_name,
                   COALESCE(SUM(t.amount), 0) as total_amount,
                   COUNT(t.transaction_id) as tx_count
            FROM categories c
            JOIN transactions t ON c.category_id = t.category_id
            WHERE t.user_id = ? AND t.transaction_type = ?
        """
        params: list = [user_id, transaction_type.upper()]

        if start_date:
            query += " AND t.transaction_date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND t.transaction_date <= ?"
            params.append(end_date)

        query += " GROUP BY c.category_id ORDER BY total_amount DESC;"
        rows = self.db.fetch_all(query, tuple(params))

        grand_total = sum(r["total_amount"] for r in rows)
        results = []
        for r in rows:
            amt = r["total_amount"]
            pct = (amt / grand_total * 100.0) if grand_total > 0 else 0.0
            results.append(
                {
                    "category": r["category_name"],
                    "count": r["tx_count"],
                    "total_amount": amt,
                    "percentage": pct,
                }
            )
        return results

    def get_income_vs_expense_report(
        self,
        user_id: int,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict:
        """
        Comparative financial statement showing Total Income, Total Expenses,
        Net Savings, and Savings Rate percentage.
        """
        query = """
            SELECT transaction_type, COALESCE(SUM(amount), 0) as total,
                   COUNT(transaction_id) as count
            FROM transactions
            WHERE user_id = ?
        """
        params: list = [user_id]
        if start_date:
            query += " AND transaction_date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND transaction_date <= ?"
            params.append(end_date)

        query += " GROUP BY transaction_type;"
        rows = self.db.fetch_all(query, tuple(params))

        inc_total = 0
        inc_count = 0
        exp_total = 0
        exp_count = 0

        for r in rows:
            if r["transaction_type"] == "INCOME":
                inc_total = r["total"]
                inc_count = r["count"]
            elif r["transaction_type"] == "EXPENSE":
                exp_total = r["total"]
                exp_count = r["count"]

        net = inc_total - exp_total
        savings_rate = (net / inc_total * 100.0) if inc_total > 0 else 0.0

        return {
            "start_date": start_date or "All-time",
            "end_date": end_date or "Present",
            "income_total": inc_total,
            "income_count": inc_count,
            "expense_total": exp_total,
            "expense_count": exp_count,
            "net_savings": net,
            "savings_rate": savings_rate,
        }

    def export_transactions_to_csv(
        self,
        user_id: int,
        transaction_type: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        custom_filepath: Path | None = None,
    ) -> tuple[bool, str, str | None]:
        """
        Export transactions to CSV file using standard Python csv module.
        Returns (success, message, file_path_str).
        """
        query = """
            SELECT t.transaction_id, t.transaction_date, t.transaction_type,
                   c.category_name, t.amount, t.description, t.created_at
            FROM transactions t
            JOIN categories c ON t.category_id = c.category_id
            WHERE t.user_id = ?
        """
        params: list = [user_id]

        if transaction_type:
            query += " AND t.transaction_type = ?"
            params.append(transaction_type.upper())

        if start_date:
            query += " AND t.transaction_date >= ?"
            params.append(start_date)

        if end_date:
            query += " AND t.transaction_date <= ?"
            params.append(end_date)

        query += " ORDER BY t.transaction_date DESC, t.transaction_id DESC;"
        rows = self.db.fetch_all(query, tuple(params))

        if not rows:
            return False, "No transactions found matching the export criteria.", None

        if custom_filepath:
            filepath = Path(custom_filepath)
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            type_tag = transaction_type.lower() if transaction_type else "all"
            filename = f"expense_tracker_export_{type_tag}_{timestamp}.csv"
            filepath = EXPORTS_DIR / filename

        try:
            filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(filepath, mode="w", newline="", encoding="utf-8") as csvfile:
                writer = csv.writer(csvfile)

                # Header row
                writer.writerow(
                    [
                        "Transaction ID",
                        "Date",
                        "Type",
                        "Category",
                        "Amount (INR)",
                        "Description",
                        "Created At",
                    ]
                )

                # Data rows
                for r in rows:
                    amt_rupees = f"{paise_to_rupees(r['amount']):.2f}"
                    writer.writerow(
                        [
                            r["transaction_id"],
                            r["transaction_date"],
                            r["transaction_type"],
                            r["category_name"],
                            amt_rupees,
                            r["description"] or "",
                            r["created_at"],
                        ]
                    )

            return True, f"Exported {len(rows)} records to CSV successfully!", str(filepath)
        except Exception as e:
            return False, f"Failed to export CSV: {str(e)}", None
