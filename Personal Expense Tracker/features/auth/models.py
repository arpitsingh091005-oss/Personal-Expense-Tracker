"""
User Domain Model for Authentication Feature.
"""


class User:
    """Represents an authenticated user in the system."""

    def __init__(self, user_id: int, username: str, email: str, created_at: str = ""):
        self.user_id = user_id
        self.username = username
        self.email = email
        self.created_at = created_at

    def __repr__(self):
        return f"<User id={self.user_id} username='{self.username}'>"

    def to_dict(self) -> dict:
        """Convert user instance to dictionary."""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "email": self.email,
            "created_at": self.created_at,
        }
