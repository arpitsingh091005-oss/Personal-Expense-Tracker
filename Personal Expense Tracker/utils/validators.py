"""
Input Validation Functions.
Provides robust checks for usernames, emails, passwords, financial amounts, and dates.
"""

import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from config import (
    USERNAME_MIN_LENGTH,
    USERNAME_MAX_LENGTH,
    PASSWORD_MIN_LENGTH,
    PAISE_PER_RUPEE,
)

# Standard regex for email validation
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
USERNAME_REGEX = re.compile(r"^[a-zA-Z0-9_]+$")


def validate_username(username: str) -> tuple[bool, str]:
    """
    Validate that username is non-empty, within length bounds, and alphanumeric/underscore.
    """
    if not username or not username.strip():
        return False, "Username cannot be empty."

    username = username.strip()
    if len(username) < USERNAME_MIN_LENGTH:
        return False, f"Username must be at least {USERNAME_MIN_LENGTH} characters long."
    if len(username) > USERNAME_MAX_LENGTH:
        return False, f"Username cannot exceed {USERNAME_MAX_LENGTH} characters."
    if not USERNAME_REGEX.match(username):
        return False, "Username can only contain letters, numbers, and underscores (_)."

    return True, username


def validate_email(email: str) -> tuple[bool, str]:
    """
    Validate that email follows standard email syntax.
    """
    if not email or not email.strip():
        return False, "Email address cannot be empty."

    email = email.strip()
    if not EMAIL_REGEX.match(email):
        return False, "Invalid email address format (example: name@domain.com)."

    return True, email.lower()


def validate_password(password: str) -> tuple[bool, str]:
    """
    Validate that password meets minimum length requirements and isn't purely whitespace.
    """
    if not password:
        return False, "Password cannot be empty."

    if len(password) < PASSWORD_MIN_LENGTH:
        return False, f"Password must be at least {PASSWORD_MIN_LENGTH} characters long."

    # Verify password has at least one letter and at least one non-whitespace character
    if password.isspace():
        return False, "Password cannot consist solely of whitespace."

    return True, ""


def parse_amount_to_paise(amount_str: str) -> tuple[bool, int, str]:
    """
    Safely parse user amount string into integer paise.
    Using Decimal prevents IEEE-754 floating-point inaccuracies.
    Returns (success, amount_in_paise, error_message).
    """
    if not amount_str or not amount_str.strip():
        return False, 0, "Amount cannot be empty."

    cleaned = amount_str.strip().replace(",", "")
    try:
        val = Decimal(cleaned)
    except InvalidOperation:
        return False, 0, "Amount must be a valid numeric value (e.g. 250 or 1500.50)."

    if val <= Decimal(0):
        return False, 0, "Amount must be strictly greater than zero."

    # Check decimal places (cannot have more than 2 decimal places for paise)
    if val.as_tuple().exponent < -2:
        return False, 0, "Amount cannot have more than 2 decimal places."

    # Maximum reasonable financial limit (100 Crores = 1,000,000,000)
    if val > Decimal(1_000_000_000):
        return False, 0, "Amount exceeds maximum allowable threshold (₹1,000,000,000)."

    # Convert to integer paise
    paise = int(val * PAISE_PER_RUPEE)
    return True, paise, ""


def validate_date(date_str: str) -> tuple[bool, str, str]:
    """
    Validate date string format (YYYY-MM-DD) and check that it represents a real calendar date.
    Returns (success, normalized_date_str, error_message).
    """
    if not date_str or not date_str.strip():
        return False, "", "Date cannot be empty."

    date_str = date_str.strip()
    try:
        parsed_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return False, "", "Invalid date format. Please use YYYY-MM-DD (e.g. 2026-11-19)."

    # Sanity bounds: between year 2000 and 2100
    if parsed_date.year < 2000 or parsed_date.year > 2100:
        return False, "", "Date year must be between 2000 and 2100."

    return True, parsed_date.strftime("%Y-%m-%d"), ""


def validate_month_year(month: int, year: int) -> tuple[bool, str]:
    """
    Validate month (1-12) and year (2000-2100).
    """
    if not (1 <= month <= 12):
        return False, "Month must be between 1 (January) and 12 (December)."
    if not (2000 <= year <= 2100):
        return False, "Year must be between 2000 and 2100."
    return True, ""
