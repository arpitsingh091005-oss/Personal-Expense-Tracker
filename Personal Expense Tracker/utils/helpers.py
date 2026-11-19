"""
Helper Utilities for Formatting, Console Display, and Tables.
Provides a clean, professional command-line interface.
"""

import os
from datetime import datetime
from config import CURRENCY_SYMBOL, PAISE_PER_RUPEE


def paise_to_rupees(paise: int) -> float:
    """Convert integer paise to float rupees."""
    return paise / PAISE_PER_RUPEE


def format_currency(paise: int, include_symbol: bool = True) -> str:
    """
    Format integer paise into standard Indian/International currency representation.
    Example: 1545075 paise -> '₹ 15,450.75'
    """
    is_negative = paise < 0
    abs_paise = abs(paise)
    rupees = abs_paise // PAISE_PER_RUPEE
    remaining_paise = abs_paise % PAISE_PER_RUPEE

    # Format rupees with commas
    formatted_rupees = f"{rupees:,}"
    formatted = f"{formatted_rupees}.{remaining_paise:02d}"

    prefix = "-" if is_negative else ""
    symbol = f"{CURRENCY_SYMBOL} " if include_symbol else ""
    return f"{prefix}{symbol}{formatted}"


def format_date(date_str: str) -> str:
    """Format YYYY-MM-DD to DD-b-YYYY (e.g. '19-Nov-2026')."""
    if not date_str:
        return "N/A"
    try:
        dt = datetime.strptime(str(date_str).split()[0], "%Y-%m-%d")
        return dt.strftime("%d-%b-%Y")
    except ValueError:
        return str(date_str)


def clear_screen():
    """Clear terminal screen in a cross-platform manner."""
    os.system("cls" if os.name == "nt" else "clear")


def print_header(title: str, subtitle: str = ""):
    """Print an attractive section header with borders."""
    width = 60
    print("\n" + "=" * width)
    print(title.center(width))
    if subtitle:
        print(f"({subtitle})".center(width))
    print("=" * width)


def print_success(message: str):
    """Display a success notice."""
    print(f"\n[SUCCESS] {message}")


def print_error(message: str):
    """Display an error notice."""
    print(f"\n[ERROR] {message}")


def print_alert(message: str):
    """Display a warning/alert notice."""
    print(f"\n[WARNING] {message}")


def print_table(
    headers: list[str],
    rows: list[list[str]],
    alignments: list[str] = None,
    empty_message: str = "No records found.",
):
    """
    Render a clean ASCII table with automatic column sizing.
    alignments: list of 'L' (left) or 'R' (right) for each column.
    """
    if not rows:
        print(f"\n[i] {empty_message}")
        return

    col_count = len(headers)
    # Default alignment: numbers or currency right, rest left
    if not alignments or len(alignments) != col_count:
        alignments = ["L"] * col_count

    # Determine maximum width for each column
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, val in enumerate(row):
            if i < col_count:
                col_widths[i] = max(col_widths[i], len(str(val)))

    # Add 2 characters padding (1 left, 1 right)
    col_widths = [w + 2 for w in col_widths]

    # Generate separator line
    sep = "+" + "+".join("-" * w for w in col_widths) + "+"

    # Header line
    header_parts = []
    for i, h in enumerate(headers):
        header_parts.append(f" {h} ".center(col_widths[i]))
    header_line = "|" + "|".join(header_parts) + "|"

    print(sep)
    print(header_line)
    print(sep)

    # Data rows
    for row in rows:
        row_parts = []
        for i in range(col_count):
            val = str(row[i]) if i < len(row) else ""
            w = col_widths[i]
            if alignments[i] == "R":
                row_parts.append(f" {val.rjust(w - 2)} ")
            else:
                row_parts.append(f" {val.ljust(w - 2)} ")
        print("|" + "|".join(row_parts) + "|")

    print(sep)
    print(f"Total rows: {len(rows)}")


def get_input(prompt: str, default: str = None, allow_cancel: bool = False) -> str | None:
    """
    Helper to get clean user input.
    If allow_cancel is True and user inputs 'c' or 'cancel', returns None.
    """
    display_prompt = prompt
    if default is not None:
        display_prompt += f" [{default}]"
    if allow_cancel:
        display_prompt += " (type 'c' to cancel)"
    display_prompt += ": "

    try:
        user_input = input(display_prompt).strip()
    except (KeyboardInterrupt, EOFError):
        print("\nOperation cancelled.")
        return None

    if allow_cancel and user_input.lower() in ("c", "cancel"):
        return None

    if not user_input and default is not None:
        return default

    return user_input


def pause():
    """Prompt the user to press Enter to continue."""
    try:
        input("\nPress Enter to return to menu...")
    except (KeyboardInterrupt, EOFError):
        pass
