"""
Configuration Module for Personal Expense Tracker.
Contains global application constants, paths, default categories, and styling settings.
"""

import os
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).resolve().parent
DATABASE_DIR = BASE_DIR / "database"
EXPORTS_DIR = BASE_DIR / "exports"
TESTS_DIR = BASE_DIR / "tests"

# Ensure runtime directories exist
DATABASE_DIR.mkdir(parents=True, exist_ok=True)
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

# Database configuration
DATABASE_FILE_NAME = "expense_tracker.db"
DEFAULT_DB_PATH = DATABASE_DIR / DATABASE_FILE_NAME

# Financial calculation constants
# 1 Rupee = 100 Paise. Storing money as integer paise eliminates IEEE-754 floating-point rounding errors.
PAISE_PER_RUPEE = 100
CURRENCY_SYMBOL = "₹"
CURRENCY_CODE = "INR"

# Application metadata
APP_TITLE = "PERSONAL EXPENSE TRACKER"
APP_SUBTITLE = "MCA 3rd Year Minor Project - Core Python & SQLite3"
APP_VERSION = "1.0.0"

# Default categories seeded on initialization
DEFAULT_INCOME_CATEGORIES = [
    "Salary",
    "Freelancing",
    "Business",
    "Investment",
    "Other",
]

DEFAULT_EXPENSE_CATEGORIES = [
    "Food",
    "Travel",
    "Shopping",
    "Education",
    "Entertainment",
    "Medical",
    "Bills",
    "Others",
]

# Validation rules
USERNAME_MIN_LENGTH = 3
USERNAME_MAX_LENGTH = 30
PASSWORD_MIN_LENGTH = 6
PASSWORD_SALT_BYTES = 16
PBKDF2_ITERATIONS = 100000

# Budget alert thresholds
BUDGET_WARNING_THRESHOLD_PERCENT = 80.0
