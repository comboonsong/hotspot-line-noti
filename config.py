import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration loaded from environment variables."""

    def __init__(self):
        load_dotenv()

        # LINE Messaging API
        self.LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
        self.LINE_GROUP_ID = os.getenv("LINE_GROUP_ID", "")

        # Province filter
        self.PROVINCE_FILTER = os.getenv("PROVINCE_FILTER", "ลำพูน")

        # Schedule times (comma-separated, e.g. "06:00,14:00")
        self.SCHEDULE_TIMES = os.getenv(
            "SCHEDULE_TIMES", "05:25,11:00,12:00,13:00,14:00,15:00,16:00,17:00"
        ).split(",")

        # Explicit time window for this run (set by GitHub Actions)
        # Format: "HH:MM" e.g. "05:25" — empty string means no bound
        self.WINDOW_START = os.getenv("WINDOW_START", "")
        self.WINDOW_END   = os.getenv("WINDOW_END",   "")

        # Message format: "satellite", "district", or "both"
        self.MESSAGE_MODE = os.getenv("MESSAGE_MODE", "satellite")

    def validate(self) -> None:
        """Validate that required config values are set."""
        print(f"DEBUG: LINE_CHANNEL_ACCESS_TOKEN present? {'Yes' if self.LINE_CHANNEL_ACCESS_TOKEN else 'No'}")
        print(f"DEBUG: LINE_GROUP_ID present? {'Yes' if self.LINE_GROUP_ID else 'No'}")

        errors = []
        if not self.LINE_CHANNEL_ACCESS_TOKEN:
            errors.append("LINE_CHANNEL_ACCESS_TOKEN is not set")
        if not self.LINE_GROUP_ID:
            errors.append("LINE_GROUP_ID is not set")
        if errors:
            raise ValueError(
                "Configuration errors:\n" + "\n".join(f"  - {e}" for e in errors)
            )
