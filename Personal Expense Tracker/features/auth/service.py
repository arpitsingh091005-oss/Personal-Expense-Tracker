"""
Authentication Feature Service.
Handles user registration, login, secure password hashing using PBKDF2 HMAC SHA-256,
password updates, and user session management.
"""

import os
import hashlib
import hmac
import sqlite3
from config import PBKDF2_ITERATIONS, PASSWORD_SALT_BYTES
from database import DatabaseManager, db
from utils.validators import validate_username, validate_email, validate_password
from features.auth.models import User


class AuthService:
    """Provides authentication and user identity services."""

    def __init__(self, db_manager: DatabaseManager = db):
        self.db = db_manager

    @staticmethod
    def _hash_password(password: str, salt_hex: str) -> str:
        """Compute PBKDF2-HMAC-SHA256 hash using the provided salt."""
        salt_bytes = bytes.fromhex(salt_hex)
        hash_bytes = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt_bytes,
            PBKDF2_ITERATIONS,
        )
        return hash_bytes.hex()

    def register(
        self, username: str, email: str, password: str
    ) -> tuple[bool, str, User | None]:
        """
        Register a new user after validating username, email, and password.
        Guarantees uniqueness of username and email.
        """
        u_valid, u_res = validate_username(username)
        if not u_valid:
            return False, u_res, None
        clean_username = u_res

        e_valid, e_res = validate_email(email)
        if not e_valid:
            return False, e_res, None
        clean_email = e_res

        p_valid, p_err = validate_password(password)
        if not p_valid:
            return False, p_err, None

        # Check for duplicate username or email
        existing = self.db.fetch_one(
            "SELECT user_id, username, email FROM users WHERE username = ? OR email = ?;",
            (clean_username, clean_email),
        )
        if existing:
            if existing["username"].lower() == clean_username.lower():
                return False, f"Username '{clean_username}' is already registered.", None
            if existing["email"].lower() == clean_email.lower():
                return False, f"Email '{clean_email}' is already registered.", None

        # Generate cryptographically secure salt and hash
        salt_bytes = os.urandom(PASSWORD_SALT_BYTES)
        salt_hex = salt_bytes.hex()
        password_hash = self._hash_password(password, salt_hex)

        try:
            with self.db.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO users (username, email, password_hash, salt)
                    VALUES (?, ?, ?, ?);
                    """,
                    (clean_username, clean_email, password_hash, salt_hex),
                )
                user_id = cursor.lastrowid

            user = User(user_id=user_id, username=clean_username, email=clean_email)
            return True, "Registration successful!", user

        except sqlite3.IntegrityError:
            return False, "User with this username or email already exists.", None
        except Exception as e:
            return False, f"Database error during registration: {str(e)}", None

    def login(
        self, username_or_email: str, password: str
    ) -> tuple[bool, str, User | None]:
        """
        Authenticate user with username or email and password.
        Uses constant-time comparison (hmac.compare_digest) to prevent timing attacks.
        """
        if not username_or_email or not username_or_email.strip():
            return False, "Please enter your username or email.", None
        if not password:
            return False, "Please enter your password.", None

        identifier = username_or_email.strip()

        row = self.db.fetch_one(
            """
            SELECT user_id, username, email, password_hash, salt, created_at
            FROM users
            WHERE username = ? OR email = ?;
            """,
            (identifier, identifier.lower()),
        )

        if not row:
            return False, "Invalid username/email or password.", None

        stored_hash = row["password_hash"]
        salt_hex = row["salt"]
        computed_hash = self._hash_password(password, salt_hex)

        if not hmac.compare_digest(stored_hash, computed_hash):
            return False, "Invalid username/email or password.", None

        user = User(
            user_id=row["user_id"],
            username=row["username"],
            email=row["email"],
            created_at=row["created_at"],
        )
        return True, "Login successful!", user

    def change_password(
        self, user_id: int, old_password: str, new_password: str
    ) -> tuple[bool, str]:
        """Change user password after verifying the existing password."""
        row = self.db.fetch_one(
            "SELECT password_hash, salt FROM users WHERE user_id = ?;",
            (user_id,),
        )
        if not row:
            return False, "User not found."

        stored_hash = row["password_hash"]
        salt_hex = row["salt"]
        computed_hash = self._hash_password(old_password, salt_hex)

        if not hmac.compare_digest(stored_hash, computed_hash):
            return False, "Current password verification failed."

        valid_new, err_msg = validate_password(new_password)
        if not valid_new:
            return False, err_msg

        if old_password == new_password:
            return False, "New password cannot be the same as the old password."

        # Generate new salt and new hash
        new_salt_hex = os.urandom(PASSWORD_SALT_BYTES).hex()
        new_hash = self._hash_password(new_password, new_salt_hex)

        self.db.execute_non_query(
            "UPDATE users SET password_hash = ?, salt = ? WHERE user_id = ?;",
            (new_hash, new_salt_hex, user_id),
        )
        return True, "Password updated successfully!"

    def get_user_by_id(self, user_id: int) -> User | None:
        """Fetch user by primary key."""
        row = self.db.fetch_one(
            "SELECT user_id, username, email, created_at FROM users WHERE user_id = ?;",
            (user_id,),
        )
        if row:
            return User(
                user_id=row["user_id"],
                username=row["username"],
                email=row["email"],
                created_at=row["created_at"],
            )
        return None
