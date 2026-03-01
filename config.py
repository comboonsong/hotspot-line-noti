import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration loaded from environment variables."""

    # LINE Messaging API
    LINE_CHANNEL_ACCESS_TOKEN: str = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
    LINE_GROUP_ID: str = os.getenv("LINE_GROUP_ID", "")

    # GISTDA API (kept for potential future use)
    GISTDA_API_KEY: str = os.getenv(
        "GISTDA_API_KEY",
        "LnCj76b2hiFrn6DzAsPR6gEk9HT1sa1epEFlL4gOELa8mzsyJ5hunfzcwoTvX1Sd",
    )

    # Province filter (ลำพูน)
    PROVINCE_FILTER: str = os.getenv("PROVINCE_FILTER", "ลำพูน")

    # Schedule times (comma-separated, e.g. "06:00,14:00")
    SCHEDULE_TIMES: list[str] = os.getenv(
        "SCHEDULE_TIMES", "01:00,03:00,06:00,14:00"
    ).split(",")

    # FIRMS API
    FIRMS_MAP_KEY: str = os.getenv(
        "FIRMS_MAP_KEY", "369c072d72f9f4b7eebc861b88b245f9"
    )
    FIRMS_THA_BBOX: str = "97.229004,5.484768,105.732422,20.612220"
    FIRMS_SOURCES: list[str] = [
        "VIIRS_SNPP_NRT",
        "VIIRS_NOAA20_NRT",
        "VIIRS_NOAA21_NRT",
    ]

    # FIRMS source → GISTDA satellite name mapping
    FIRMS_TO_GISTDA_SAT: dict[str, str] = {
        "VIIRS_SNPP_NRT": "N_Vi1",
        "VIIRS_NOAA20_NRT": "N_Vi2",
        "VIIRS_NOAA21_NRT": "N_Vi3",
    }

    # GISTDA satellite name → display name
    GISTDA_SAT_DISPLAY: dict[str, str] = {
        "N_Vi1": "Suomi NPP",
        "N_Vi2": "NOAA-20",
        "N_Vi3": "NOAA-21",
    }

    # GISTDA Excel base URL
    GISTDA_EXCEL_BASE_URL: str = "https://disaster.gistda.or.th/api/v2/file/download"

    def validate(self) -> None:
        """Validate that required config values are set."""
        errors = []
        if not self.LINE_CHANNEL_ACCESS_TOKEN:
            errors.append("LINE_CHANNEL_ACCESS_TOKEN is not set")
        if not self.LINE_GROUP_ID:
            errors.append("LINE_GROUP_ID is not set")
        if not self.FIRMS_MAP_KEY:
            errors.append("FIRMS_MAP_KEY is not set")
        if errors:
            raise ValueError(
                "Configuration errors:\n" + "\n".join(f"  - {e}" for e in errors)
            )
