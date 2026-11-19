"""
Feature-Based Architecture Package.
Organizes business logic into vertical domain slices:
- auth: User registration, login, PBKDF2 hashing, sessions
- income: Income tracking, history, source categorization
- expenses: Expense tracking, budget overdraft interception
- categories: System default and user-defined custom categories
- budget: Monthly spending limits, calculations, 80%/100% threshold alerts
- dashboard: High-level financial KPIs, balances, net cash flow
- reports: Daily, weekly, monthly, yearly analytics, CSV export
"""
