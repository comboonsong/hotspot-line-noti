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

        # GISTDA API (kept for potential future use)
        self.GISTDA_API_KEY = os.getenv("GISTDA_API_KEY", "")

        # Province filter (ลำพูน)
        self.PROVINCE_FILTER = os.getenv("PROVINCE_FILTER", "ลำพูน")

        # Schedule times (comma-separated, e.g. "06:00,14:00")
        self.SCHEDULE_TIMES = os.getenv(
            "SCHEDULE_TIMES", "01:00,03:00,06:00,14:00"
        ).split(",")

        # FIRMS API
        self.FIRMS_MAP_KEY = os.getenv("FIRMS_MAP_KEY", "")
        self.FIRMS_THA_BBOX = "97.229004,5.484768,105.732422,20.612220"
        self.FIRMS_SOURCES = [
            "VIIRS_SNPP_NRT",
            "VIIRS_NOAA20_NRT",
            "VIIRS_NOAA21_NRT",
        ]

        # FIRMS source → GISTDA satellite name mapping
        self.FIRMS_TO_GISTDA_SAT = {
            "VIIRS_SNPP_NRT": "N_Vi1",
            "VIIRS_NOAA20_NRT": "N_Vi2",
            "VIIRS_NOAA21_NRT": "N_Vi3",
        }

        # GISTDA satellite name → display name
        self.GISTDA_SAT_DISPLAY = {
            "N_Vi1": "Suomi NPP",
            "N_Vi2": "NOAA-20",
            "N_Vi3": "NOAA-21",
            "G_Vi1": "Suomi NPP - GISTDA",
        }

        # NASA folder → GISTDA folder mapping
        self.GISTDA_FOLDER_MAP = {
            "N_Vi1": ("G_Vi1", "Suomi NPP - GISTDA"),
        }

        # GISTDA Excel base URL
        self.GISTDA_EXCEL_BASE_URL = "https://disaster.gistda.or.th/api/v2/file/download"

        # Time spread for exact match tolerance (minutes)
        self.TIME_SPREAD = int(os.getenv("TIME_SPREAD", "5"))
        self.GISTDA_TIME_SPREAD = int(os.getenv("GISTDA_TIME_SPREAD", "10"))

    def validate(self) -> None:
        """Validate that required config values are set."""
        # Safe debug prints (won't show values, just presence)
        print(f"DEBUG: LINE_CHANNEL_ACCESS_TOKEN present? {'Yes' if self.LINE_CHANNEL_ACCESS_TOKEN else 'No'}")
        print(f"DEBUG: LINE_GROUP_ID present? {'Yes' if self.LINE_GROUP_ID else 'No'}")
        print(f"DEBUG: FIRMS_MAP_KEY present? {'Yes' if self.FIRMS_MAP_KEY else 'No'}")

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
