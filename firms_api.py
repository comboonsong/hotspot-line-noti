"""
FIRMS API client — discover satellite pass times over Thailand.

Queries NASA FIRMS for VIIRS hotspot data and identifies unique
satellite pass times on the current Thai date (UTC+7).
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from io import StringIO

import pandas as pd
import requests

logger = logging.getLogger(__name__)

# Thailand timezone (UTC+7)
TZ_BANGKOK = timezone(timedelta(hours=7))

# FIRMS API base URL
FIRMS_BASE_URL = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"


@dataclass
class PassTime:
    """Represents a unique satellite pass time."""

    gistda_sat_name: str     # e.g. "N_Vi1"
    display_name: str        # e.g. "Suomi NPP"
    thai_date: str           # e.g. "20260226"
    thai_time: str           # e.g. "0201"
    hotspot_count: int       # number of hotspots in this pass


def _utc_to_thai(acq_date: str, acq_time: str) -> datetime:
    """
    Convert FIRMS UTC acquisition date+time to Thai datetime.

    Args:
        acq_date: Date string like "2026-02-25".
        acq_time: Time string like "1901" (HHMM in UTC).

    Returns:
        datetime in Thai timezone (UTC+7).
    """
    hour = int(acq_time[:2])
    minute = int(acq_time[2:])
    dt_utc = datetime.strptime(acq_date, "%Y-%m-%d").replace(
        hour=hour, minute=minute, tzinfo=timezone.utc
    )
    return dt_utc.astimezone(TZ_BANGKOK)


def discover_pass_times(
    map_key: str,
    bbox: str,
    sources: list[str],
    firms_to_gistda: dict[str, str],
    sat_display: dict[str, str],
    today_date: datetime | None = None,
    date_range: int = 2,
) -> list[PassTime]:
    """
    Query FIRMS API for each satellite source and discover unique
    pass times that fall on today's Thai date.

    Args:
        map_key: FIRMS MAP_KEY for authentication.
        bbox: Bounding box string "west,south,east,north".
        sources: List of FIRMS source names (e.g. "VIIRS_SNPP_NRT").
        firms_to_gistda: Mapping from FIRMS source to GISTDA sat name.
        sat_display: Mapping from GISTDA sat name to display name.
        today_date: Override for "today" in Thai timezone. Defaults to now.
        date_range: Number of days to query from FIRMS (default 1).

    Returns:
        List of PassTime objects, sorted by (thai_time, satellite order).
    """
    if today_date is None:
        today_date = datetime.now(TZ_BANGKOK)

    today_str = today_date.strftime("%Y-%m-%d")
    now_time = today_date.strftime("%H%M")

    logger.info(
        "Discovering pass times for Thai date %s (up to %sน.)",
        today_str,
        f"{now_time[:2]}:{now_time[2:]}",
    )

    all_pass_times: list[PassTime] = []

    for src in sources:
        gistda_sat = firms_to_gistda.get(src, src)
        display_name = sat_display.get(gistda_sat, gistda_sat)

        url = f"{FIRMS_BASE_URL}/{map_key}/{src}/{bbox}/{date_range}"
        logger.info("Querying FIRMS: %s (date_range=%d)", src, date_range)

        try:
            response = requests.get(url, timeout=60)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            logger.error("Failed to query FIRMS for %s: %s", src, e)
            continue

        try:
            df = pd.read_csv(StringIO(response.text))
        except Exception as e:
            logger.error("Failed to parse FIRMS CSV for %s: %s", src, e)
            continue

        if df.empty or "acq_date" not in df.columns or "acq_time" not in df.columns:
            logger.warning("No data or missing columns for %s", src)
            continue

        logger.info("FIRMS returned %d rows for %s", len(df), src)

        # Convert acq_time to zero-padded 4-digit string
        df["acq_time_str"] = df["acq_time"].astype(str).str.zfill(4)

        # Convert to Thai datetime and filter for today
        thai_dates = []
        thai_times = []
        for _, row in df.iterrows():
            try:
                thai_dt = _utc_to_thai(str(row["acq_date"]), row["acq_time_str"])
                thai_dates.append(thai_dt.strftime("%Y-%m-%d"))
                thai_times.append(thai_dt.strftime("%H%M"))
            except (ValueError, KeyError):
                thai_dates.append(None)
                thai_times.append(None)

        df["thai_date"] = thai_dates
        df["thai_time"] = thai_times

        # Filter for today's Thai date only
        df_today = df[df["thai_date"] == today_str].copy()

        # Determine start time based on current time (00:00 or 12:00)
        start_time = "0000" if now_time < "1200" else "1200"

        # Filter: start_time <= thai_time <= current time
        df_today = df_today[
            (df_today["thai_time"] >= start_time) & (df_today["thai_time"] <= now_time)
        ]

        if df_today.empty:
            logger.info("No hotspots on %s for %s", today_str, src)
            continue

        logger.info(
            "Found %d hotspots on %s for %s", len(df_today), today_str, src
        )

        # Get unique pass times
        for th_time, group in df_today.groupby("thai_time"):
            pass_time = PassTime(
                gistda_sat_name=gistda_sat,
                display_name=display_name,
                thai_date=today_str.replace("-", ""),  # "20260226"
                thai_time=str(th_time),
                hotspot_count=len(group),
            )
            all_pass_times.append(pass_time)

    # Sort by time, then satellite order
    SAT_ORDER = {"N_Vi1": 0, "N_Vi2": 1, "N_Vi3": 2}
    all_pass_times.sort(
        key=lambda pt: (pt.thai_time, SAT_ORDER.get(pt.gistda_sat_name, 99))
    )

    logger.info(
        "Discovered %d unique pass times: %s",
        len(all_pass_times),
        [(pt.display_name, pt.thai_time) for pt in all_pass_times],
    )

    return all_pass_times
