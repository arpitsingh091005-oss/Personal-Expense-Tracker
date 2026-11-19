"""
Web Server for Personal Expense Tracker.
Built using Core Python's built-in http.server (No Flask/Django/FastAPI).
Serves the HTML/CSS/JS frontend and handles REST JSON API requests.
"""

import json
import mimetypes
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from pathlib import Path

from config import BASE_DIR
from database import db
from features.auth import AuthService
from features.categories import CategoryService
from features.income import IncomeService
from features.expenses import ExpenseService
from features.budget import BudgetService
from features.dashboard import DashboardService
from features.reports import ReportService
from utils.validators import parse_amount_to_paise

WEB_DIR = BASE_DIR / "web"


class ExpenseTrackerWebHandler(BaseHTTPRequestHandler):
    """Handles static web requests and REST JSON API endpoints."""

    # Initialize services
    auth_service = AuthService(db)
    cat_service = CategoryService(db)
    income_service = IncomeService(db)
    expense_service = ExpenseService(db)
    budget_service = BudgetService(db)
    dashboard_service = DashboardService(db)
    report_service = ReportService(db)

    def _send_json(self, status: int, payload: dict):
        """Send JSON response with proper headers."""
        data = json.dumps(payload, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)

    def _serve_file(self, filepath: Path):
        """Serve static HTML/CSS/JS asset."""
        if not filepath.exists() or not filepath.is_file():
            self.send_error(404, f"File Not Found: {filepath.name}")
            return

        mime_type, _ = mimetypes.guess_type(str(filepath))
        mime_type = mime_type or "application/octet-stream"

        try:
            with open(filepath, "rb") as f:
                content = f.read()

            self.send_response(200)
            self.send_header("Content-Type", f"{mime_type}; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_error(500, f"Error reading file: {str(e)}")

    def do_GET(self):
        """Handle GET requests for static files and API queries."""
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        # 1. API: Get Dashboard Summary
        if path == "/api/summary":
            u_id = int(query.get("user_id", [1])[0])
            summary = self.dashboard_service.get_financial_summary(u_id)
            self._send_json(200, {"success": True, "data": summary})
            return

        # 2. API: Get Transactions (filtered or all)
        elif path == "/api/transactions":
            u_id = int(query.get("user_id", [1])[0])
            tx_type = query.get("type", [None])[0]
            if tx_type == "INCOME":
                rows = self.income_service.get_incomes(u_id)
            elif tx_type == "EXPENSE":
                rows = self.expense_service.get_expenses(u_id)
            else:
                inc = self.income_service.get_incomes(u_id)
                exp = self.expense_service.get_expenses(u_id)
                rows = sorted(
                    list(inc) + list(exp),
                    key=lambda x: (x["transaction_date"], x["transaction_id"]),
                    reverse=True,
                )

            data = [dict(r) for r in rows]
            self._send_json(200, {"success": True, "data": data})
            return

        # 3. API: Get Categories
        elif path == "/api/categories":
            u_id = int(query.get("user_id", [1])[0])
            cat_type = query.get("type", [None])[0]
            cats = self.cat_service.get_categories(u_id, cat_type)
            self._send_json(200, {"success": True, "data": [dict(c) for c in cats]})
            return

        # 4. API: Get Budget
        elif path == "/api/budget":
            u_id = int(query.get("user_id", [1])[0])
            month = int(query.get("month", [11])[0])
            year = int(query.get("year", [2026])[0])
            b_info = self.budget_service.get_budget(u_id, month, year)
            all_budgets = self.budget_service.get_all_budgets(u_id)
            self._send_json(200, {"success": True, "data": b_info, "history": all_budgets})
            return

        # 5. API: Direct CSV Download
        elif path == "/api/export-csv":
            u_id = int(query.get("user_id", [1])[0])
            ok, msg, filepath = self.report_service.export_transactions_to_csv(u_id)
            if ok and filepath:
                csv_path = Path(filepath)
                with open(csv_path, "rb") as f:
                    csv_data = f.read()

                self.send_response(200)
                self.send_header("Content-Type", "text/csv; charset=utf-8")
                self.send_header(
                    "Content-Disposition", f'attachment; filename="{csv_path.name}"'
                )
                self.send_header("Content-Length", str(len(csv_data)))
                self.end_headers()
                self.wfile.write(csv_data)
                return
            else:
                self._send_json(400, {"success": False, "message": msg})
                return

        # 6. Static File Serving
        if path in ("/", "/index.html"):
            self._serve_file(WEB_DIR / "index.html")
        elif path == "/styles.css":
            self._serve_file(WEB_DIR / "styles.css")
        elif path == "/app.js":
            self._serve_file(WEB_DIR / "app.js")
        else:
            self._serve_file(WEB_DIR / path.lstrip("/"))

    def do_POST(self):
        """Handle POST requests for JSON forms and transactions."""
        parsed = urlparse(self.path)
        path = parsed.path

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8")
        try:
            payload = json.loads(body) if body else {}
        except json.JSONDecodeError:
            self._send_json(400, {"success": False, "message": "Invalid JSON format."})
            return

        # 1. API: Login
        if path == "/api/login":
            username = payload.get("username", "")
            password = payload.get("password", "")
            ok, msg, user = self.auth_service.login(username, password)
            if ok and user:
                self._send_json(
                    200,
                    {
                        "success": True,
                        "message": msg,
                        "user": {"user_id": user.user_id, "username": user.username},
                    },
                )
            else:
                self._send_json(401, {"success": False, "message": msg})
            return

        # 2. API: Add Income
        elif path == "/api/income":
            u_id = int(payload.get("user_id", 1))
            cat_id = int(payload.get("category_id"))
            amt_str = str(payload.get("amount", ""))
            date_str = str(payload.get("date", ""))
            desc = str(payload.get("description", ""))

            valid, paise, err = parse_amount_to_paise(amt_str)
            if not valid:
                self._send_json(400, {"success": False, "message": err})
                return

            ok, msg, tx_id = self.income_service.add_income(
                u_id, cat_id, paise, date_str, desc
            )
            self._send_json(200 if ok else 400, {"success": ok, "message": msg, "id": tx_id})
            return

        # 3. API: Add Expense
        elif path == "/api/expense":
            u_id = int(payload.get("user_id", 1))
            cat_id = int(payload.get("category_id"))
            amt_str = str(payload.get("amount", ""))
            date_str = str(payload.get("date", ""))
            desc = str(payload.get("description", ""))

            valid, paise, err = parse_amount_to_paise(amt_str)
            if not valid:
                self._send_json(400, {"success": False, "message": err})
                return

            ok, msg, tx_id, warning = self.expense_service.add_expense(
                u_id, cat_id, paise, date_str, desc
            )
            self._send_json(
                200 if ok else 400,
                {"success": ok, "message": msg, "id": tx_id, "warning": warning},
            )
            return

        # 4. API: Set Budget
        elif path == "/api/budget":
            u_id = int(payload.get("user_id", 1))
            month = int(payload.get("month", 11))
            year = int(payload.get("year", 2026))
            amt_str = str(payload.get("amount", ""))

            valid, paise, err = parse_amount_to_paise(amt_str)
            if not valid:
                self._send_json(400, {"success": False, "message": err})
                return

            ok, msg, b_id = self.budget_service.set_or_update_budget(
                u_id, month, year, paise
            )
            self._send_json(200 if ok else 400, {"success": ok, "message": msg, "id": b_id})
            return

        self.send_error(404, "API route not found.")

    def do_DELETE(self):
        """Handle DELETE requests for removing transactions."""
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if path == "/api/transaction":
            u_id = int(query.get("user_id", [1])[0])
            tx_id = int(query.get("id", [0])[0])
            tx_type = query.get("type", ["EXPENSE"])[0]

            if tx_type == "INCOME":
                ok, msg = self.income_service.delete_income(u_id, tx_id)
            else:
                ok, msg = self.expense_service.delete_expense(u_id, tx_id)

            self._send_json(200 if ok else 400, {"success": ok, "message": msg})
            return

        self.send_error(404, "Endpoint not found.")


def run_web_server(port: int = 8000):
    """Start the standard library HTTP server."""
    server_address = ("127.0.0.1", port)
    try:
        httpd = HTTPServer(server_address, ExpenseTrackerWebHandler)
        print("\n" + "=" * 60)
        print("PERSONAL EXPENSE TRACKER - WEB FRONTEND".center(60))
        print("=" * 60)
        print(f"[*] Core Python HTTP Server running at:")
        print(f"    --> http://localhost:{port}")
        print(f"    --> http://127.0.0.1:{port}")
        print("=" * 60)
        print("[i] Open this URL in Chrome, Safari, or your preferred browser.")
        print("[i] Press Ctrl+C in terminal to stop the web server.\n")
        httpd.serve_forever()
    except OSError as e:
        if port == 8000:
            print(f"[!] Port 8000 busy, trying fallback port 8080...")
            run_web_server(8080)
        else:
            print(f"[ERROR] Failed to start server: {e}")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n[+] Web server stopped.")
        sys.exit(0)


if __name__ == "__main__":
    run_web_server()
