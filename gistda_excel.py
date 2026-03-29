"""
GISTDA Excel downloader & parser.

Fetches the list of available hotspot Excel files from the GISTDA
disaster portal directory API, downloads them, and parses hotspot data.

Time window logic:
- Files are pre-filtered by filename time (with 30-min buffer) to minimise downloads.
- Hotspots are filtered by COL_TIME (actual satellite acquisition time in Thai TZ).
- Returns the latest COL_TIME found among filtered hotspots for state tracking.
"""

import logging
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import requests

logger = logging.getLogger(__name__)

# Thailand timezone (UTC+7)
TZ_BANGKOK = timezone(timedelta(hours=7))

# GISTDA base URL
GISTDA_BASE_URL = "https://disaster.gistda.or.th"

# Sheet name to parse (Northern Thailand)
SHEET_NAME = "ภาคเหนือ"

# Satellite folder codes → display name
GISTDA_SOURCES = {
    "G_Vi1": "Suomi NPP - GISTDA",
    "N_Vi1": "Suomi NPP",
    "N_Vi2": "NOAA-20",
    "N_Vi3": "NOAA-21",
}

# Column indices for key fields
COL_HOTSPOT_ID = 0
COL_DATE = 1
COL_TIME = 2        # "เวลา" — actual satellite acquisition time in Thai TZ (HHMM)
COL_SUB_DISTRICT = 4
COL_DISTRICT = 5
COL_PROVINCE = 6
COL_RESPONSIBLE_AREA = 8
COL_LAND_USE = 10
COL_NEAREST_VILLAGE = 14
COL_DISTANCE_KM = 15
COL_BEARING = 16
COL_DIRECTION = 17
COL_GOOGLE_MAP = 21

# Buffer (minutes) applied to the file pre-filter start time.
# Allows for slight differences between filename timestamp and COL_TIME.
FILE_BUFFER_MINUTES = 30


# ---------------------------------------------------------------------------
# Time helpers
# ---------------------------------------------------------------------------

def _to_hhmm(time_str: str) -> str:
    """
    Normalise a time string to 4-digit HHMM format (no colon).

    Accepts: "1408", "14:08", "525", "05:25".
    Returns "0000" for unparseable input.
    """
    s = str(time_str).strip().replace(":", "")
    return s.zfill(4) if s.isdigit() and len(s) <= 4 else "0000"


def _hhmm_subtract(hhmm: str, minutes: int) -> str:
    """Subtract *minutes* from a HHMM string; result floored at '0000'."""
    total = max(0, int(hhmm[:2]) * 60 + int(hhmm[2:]) - minutes)
    return f"{total // 60:02d}{total % 60:02d}"


# ---------------------------------------------------------------------------
# Directory listing
# ---------------------------------------------------------------------------

def list_today_files(
    today: datetime | None = None,
    sources: dict[str, str] | None = None,
) -> list[dict]:
    """
    List all GISTDA Excel files available for today's Thai date.

    Args:
        today: Target datetime in Thai timezone. Defaults to now.
        sources: Mapping of folder code → display name.

    Returns:
        List of dicts with keys:
            - sat_code, display_name, filename, th_time (from filename), url
    """
    if today is None:
        today = datetime.now(TZ_BANGKOK)
    if sources is None:
        sources = GISTDA_SOURCES

    date_str = today.strftime("%Y%m%d")
    year = today.strftime("%Y")
    results: list[dict] = []

    for sat_code, display_name in sources.items():
        prefix = f"Fire/y{year}/80_Report/Excel/{sat_code}_Tim/"
        url = f"{GISTDA_BASE_URL}/api/v2/file/directory?prefix={prefix}"

        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.error("Failed to list directory for %s: %s", sat_code, e)
            continue

        files = data.get("files", [])
        logger.info("Listed %d files for %s (date=%s)", len(files), sat_code, date_str)

        for f in files:
            filename = f["path"].split("/")[-1]
            if date_str not in filename:
                continue
            try:
                file_th_time = filename.replace(".xlsx", "").split("_")[-1]
            except IndexError:
                file_th_time = "0000"

            results.append({
                "sat_code": sat_code,
                "display_name": display_name,
                "filename": filename,
                "th_time": file_th_time,   # filename timestamp (HHMM)
                "url": GISTDA_BASE_URL + f["url"],
            })

    logger.info("Total today's files: %d", len(results))
    return results


# ---------------------------------------------------------------------------
# File-level time filter (pre-filter using filename timestamp)
# ---------------------------------------------------------------------------

def _filter_files_by_window(
    files: list[dict],
    window_start_hhmm: str,
    window_end_hhmm: str,
) -> list[dict]:
    """
    Pre-filter files by filename timestamp with a safety buffer.

    Downloads only files whose filename time falls within:
        [window_start - FILE_BUFFER_MINUTES, window_end]

    The buffer ensures we don't miss files where COL_TIME is slightly
    later than the filename timestamp.

    Args:
        files: File dicts from list_today_files().
        window_start_hhmm: Exact window start in HHMM (e.g. "0525").
        window_end_hhmm:   Exact window end   in HHMM (e.g. "1100").

    Returns:
        Filtered list of file dicts.
    """
    buffered_start = _hhmm_subtract(window_start_hhmm, FILE_BUFFER_MINUTES)
    filtered = [
        f for f in files
        if buffered_start <= f["th_time"] <= window_end_hhmm
    ]
    logger.info(
        "File pre-filter [%s(buf)–%s]: %d/%d files kept",
        buffered_start, window_end_hhmm, len(filtered), len(files),
    )
    return filtered


# ---------------------------------------------------------------------------
# Excel parsing
# ---------------------------------------------------------------------------

def _parse_excel_sheet(
    filepath: str | Path,
    province_filter: str,
    sat_display_name: str,
    filename_th_time: str,
) -> list[dict]:
    """
    Parse the ภาคเหนือ sheet from a GISTDA Excel file.

    th_time for each hotspot is taken from COL_TIME (column index 2),
    which stores the actual satellite acquisition time in Thai TZ (HHMM).
    Falls back to filename_th_time if COL_TIME is missing or unparseable.

    Args:
        filepath: Path to the downloaded .xlsx file.
        province_filter: Province name to filter (e.g. "ลำพูน").
        sat_display_name: Satellite display name for the result dicts.
        filename_th_time: Fallback time from filename (HHMM).

    Returns:
        List of hotspot dicts (all rows matching province_filter).
        th_time is the actual COL_TIME from the Excel.
    """
    try:
        df = pd.read_excel(
            filepath, sheet_name=SHEET_NAME, header=0,
            dtype=str, engine="openpyxl",
        )
    except Exception as e:
        logger.error("Failed to read Excel '%s': %s", SHEET_NAME, e)
        return []

    hotspots: list[dict] = []
    for _, row in df.iterrows():
        values = row.values.tolist()

        if len(values) <= COL_GOOGLE_MAP:
            continue

        hotspot_id = str(values[COL_HOTSPOT_ID]).strip() if pd.notna(values[COL_HOTSPOT_ID]) else ""
        if not hotspot_id or hotspot_id == "nan":
            continue
        if hotspot_id in ("หมายเหตุ", "ที่มาของข้อมูล"):
            break

        province = str(values[COL_PROVINCE]).strip() if pd.notna(values[COL_PROVINCE]) else ""
        if province_filter and province != province_filter:
            continue

        # Use actual COL_TIME (Thai TZ) from Excel; fall back to filename time
        col_time_raw = str(values[COL_TIME]).strip() if pd.notna(values[COL_TIME]) else ""
        actual_th_time = _to_hhmm(col_time_raw) if col_time_raw and col_time_raw != "nan" else filename_th_time

        google_map_raw = str(values[COL_GOOGLE_MAP]).strip() if pd.notna(values[COL_GOOGLE_MAP]) else ""
        google_map_link = google_map_raw.strip('"').strip("'")

        hotspots.append({
            "hotspot_id": hotspot_id,
            "date_th": str(values[COL_DATE]).strip() if pd.notna(values[COL_DATE]) else "",
            "th_time": actual_th_time,          # actual satellite time (COL_TIME)
            "sub_district_th": str(values[COL_SUB_DISTRICT]).strip() if pd.notna(values[COL_SUB_DISTRICT]) else "",
            "district_th": str(values[COL_DISTRICT]).strip() if pd.notna(values[COL_DISTRICT]) else "",
            "province_th": province,
            "responsible_area": str(values[COL_RESPONSIBLE_AREA]).strip() if pd.notna(values[COL_RESPONSIBLE_AREA]) else "",
            "land_use": str(values[COL_LAND_USE]).strip() if pd.notna(values[COL_LAND_USE]) else "",
            "nearest_village": str(values[COL_NEAREST_VILLAGE]).strip() if pd.notna(values[COL_NEAREST_VILLAGE]) else "",
            "distance_km": str(values[COL_DISTANCE_KM]).strip() if pd.notna(values[COL_DISTANCE_KM]) else "",
            "direction": str(values[COL_DIRECTION]).strip() if pd.notna(values[COL_DIRECTION]) else "",
            "google_maps_link": google_map_link,
            "satellite_name": sat_display_name,
        })

    return hotspots


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def download_and_parse_excel(
    now: datetime | None = None,
    province_filter: str = "ลำพูน",
    sources: dict[str, str] | None = None,
    window_start: str = "",
    window_end: str = "",
) -> tuple[list[dict], int, str]:
    """
    List, download, and parse GISTDA Excel files for today's date.

    Steps:
      1. List today's files via GISTDA directory API.
      2. Pre-filter files by filename timestamp (with 30-min buffer).
      3. Download each file and parse province-filtered hotspots.
      4. Filter hotspots by actual COL_TIME against the exact window.
      5. Return the list of hotspots within the window, the download count,
         and the latest hotspot COL_TIME (for state tracking).

    Args:
        now: Target datetime in Thai TZ. Defaults to current time.
        province_filter: Province name to filter hotspots.
        sources: Satellite source mapping.
        window_start: Window start in HHMM or HH:MM (e.g. "0525" or "05:25").
                      Empty → "0000".
        window_end:   Window end   in HHMM or HH:MM (e.g. "1100").
                      Empty → current time.

    Returns:
        Tuple (hotspots_in_window, files_downloaded, latest_hotspot_time).
        latest_hotspot_time is the max COL_TIME among hotspots, or "" if none.
    """
    if now is None:
        now = datetime.now(TZ_BANGKOK)

    # Normalise window to HHMM
    start_hhmm = _to_hhmm(window_start) if window_start else "0000"
    end_hhmm   = _to_hhmm(window_end)   if window_end   else now.strftime("%H%M")

    logger.info("Window: %s – %s (HHMM)", start_hhmm, end_hhmm)

    # 1. List today's files
    all_files = list_today_files(today=now, sources=sources)
    if not all_files:
        logger.info("No Excel files found for today.")
        return [], 0, ""

    # 2. Pre-filter files by filename timestamp (+buffer)
    candidate_files = _filter_files_by_window(all_files, start_hhmm, end_hhmm)
    if not candidate_files:
        logger.info("No files in/near window %s–%s.", start_hhmm, end_hhmm)
        return [], 0, ""

    # 3. Download & parse (deduplicated by filename)
    seen: set[str] = set()
    all_parsed: list[dict] = []
    files_downloaded = 0

    for file_info in candidate_files:
        filename = file_info["filename"]
        if filename in seen:
            continue
        seen.add(filename)

        logger.info("Downloading: %s", filename)
        try:
            resp = requests.get(file_info["url"], timeout=30)
            resp.raise_for_status()
        except Exception as e:
            logger.error("Download failed for %s: %s", filename, e)
            continue

        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            tmp.write(resp.content)
            tmp_path = tmp.name

        parsed = _parse_excel_sheet(
            filepath=tmp_path,
            province_filter=province_filter,
            sat_display_name=file_info["display_name"],
            filename_th_time=file_info["th_time"],
        )
        files_downloaded += 1
        all_parsed.extend(parsed)

        try:
            Path(tmp_path).unlink()
        except OSError:
            pass

    # 4. Filter hotspots by COL_TIME (exact window — no buffer)
    # To avoid notifying the exact same time from the previous run's latest hotspot,
    # we use strictly greater than (>), unless the window starts at "0000" (daily reset).
    hotspots_in_window = []
    for h in all_parsed:
        is_after_start = (start_hhmm <= h["th_time"]) if start_hhmm == "0000" else (start_hhmm < h["th_time"])
        if is_after_start and h["th_time"] <= end_hhmm:
            hotspots_in_window.append(h)

    logger.info(
        "Hotspot filter [%s–%s]: %d/%d hotspots kept for %s",
        start_hhmm, end_hhmm, len(hotspots_in_window), len(all_parsed), province_filter,
    )

    # 5. Latest hotspot time (max COL_TIME among filtered hotspots)
    latest_hotspot_time = max(
        (h["th_time"] for h in hotspots_in_window), default=""
    )
    if latest_hotspot_time:
        logger.info("Latest hotspot time in window: %s", latest_hotspot_time)

    return hotspots_in_window, files_downloaded, latest_hotspot_time
