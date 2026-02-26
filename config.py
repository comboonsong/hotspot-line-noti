import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration loaded from environment variables."""

    # LINE Messaging API
    LINE_CHANNEL_ACCESS_TOKEN: str = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
    LINE_GROUP_ID: str = os.getenv("LINE_GROUP_ID", "")

    # GISTDA API
    GISTDA_API_KEY: str = os.getenv(
        "GISTDA_API_KEY",
        "LnCj76b2hiFrn6DzAsPR6gEk9HT1sa1epEFlL4gOELa8mzsyJ5hunfzcwoTvX1Sd",
    )
    GISTDA_BASE_URL: str = (
        "https://api-gateway.gistda.or.th/api/2.0/resources/features/viirs/1day"
    )

    # Province (51 = ลำพูน)
    PROVINCE_IDN: int = int(os.getenv("PROVINCE_IDN", "51"))

    # Schedule times (comma-separated, e.g. "06:00,14:00")
    SCHEDULE_TIMES: list[str] = os.getenv("SCHEDULE_TIMES", "01:00,03:00,06:00,14:00").split(",")

    # API fetch limit
    FETCH_LIMIT: int = int(os.getenv("FETCH_LIMIT", "1000"))

    def validate(self) -> None:
        """Validate that required config values are set."""
        errors = []
        if not self.LINE_CHANNEL_ACCESS_TOKEN:
            errors.append("LINE_CHANNEL_ACCESS_TOKEN is not set")
        if not self.LINE_GROUP_ID:
            errors.append("LINE_GROUP_ID is not set")
        if not self.GISTDA_API_KEY:
            errors.append("GISTDA_API_KEY is not set")
        if errors:
            raise ValueError("Configuration errors:\n" + "\n".join(f"  - {e}" for e in errors))
