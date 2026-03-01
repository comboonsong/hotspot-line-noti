"""
GISTDA Excel downloader & parser.

Downloads hotspot report Excel files from GISTDA based on satellite
pass times discovered by the FIRMS API, then parses the "ภาคเหนือ"
sheet to extract hotspot data.
"""

import logging
import tempfile
from pathlib import Path

import pandas as pd
import requests

logger = logging.getLogger(__name__)

# GISTDA Excel download base URL
GISTDA_DOWNLOAD_URL = "https://disaster.gistda.or.th/api/v2/file/download"

# Sheet name to parse (Northern Thailand)
SHEET_NAME = "ภาคเหนือ"

# Expected column names in the Excel sheet (by position index)
# 0: รหัส HotSpot
# 1: วัน
# 2: เวลา
# 3: รหัสตำบล
# 4: ตำบล (hotspot location)
# 5: อำเภอ (hotspot location)
# 6: จังหวัด (hotspot location)
# 7: รหัสรับผิดชอบ
# 8: พื้นที่รับผิดชอบ
# 9: รหัสการใช้ที่ดิน
# 10: การใช้ที่ดิน
# 11: UTM_Zone
# 12: UTM East
# 13: UTM North
# 14: จุดใกล้หมู่บ้าน
# 15: ห่างหมู่บ้าน(กม)
# 16: องศาจากหมู่บ้าน
# 17: ทิศจากหมู่บ้าน
# 18: ตำบล (nearest village)
# 19: อำเภอ (nearest village)
# 20: จังหวัด (nearest village)
# 21: Link Google Map

# Column indices for key fields
COL_HOTSPOT_ID = 0
COL_DATE = 1
COL_TIME = 2
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


def _build_excel_url(sat_name: str, date_str: str, time_str: str) -> str:
    """
    Build the GISTDA Excel download URL.

    Args:
        sat_name: GISTDA satellite name (e.g. "N_Vi1").
        date_str: Thai date as "yyyymmdd" (e.g. "20260226").
        time_str: Thai time as "HHMM" (e.g. "0201").

    Returns:
        Full download URL.
    """
    year = date_str[:4]
    file_path = (
        f"Fire/y{year}/80_Report/Excel/"
        f"{sat_name}_Tim/{sat_name}_{date_str}_{time_str}.xlsx"
    )
    return f"{GISTDA_DOWNLOAD_URL}?f={file_path}"


def _parse_excel_sheet(
    filepath: str | Path,
    province_filter: str = "ลำพูน",
    sat_display_name: str = "",
    th_time: str = "",
) -> list[dict]:
    """
    Parse the "ภาคเหนือ" sheet from a GISTDA Excel file.

    Args:
        filepath: Path to the downloaded .xlsx file.
        province_filter: Province name to filter (e.g. "ลำพูน").
        sat_display_name: Satellite display name for the result dicts.
        th_time: Thai time string for the result dicts.

    Returns:
        List of hotspot dicts filtered by province.
    """
    try:
        df = pd.read_excel(
            filepath,
            sheet_name=SHEET_NAME,
            header=0,
            dtype=str,
        )
    except Exception as e:
        logger.error("Failed to read Excel sheet '%s': %s", SHEET_NAME, e)
        return []

    hotspots = []
    for _, row in df.iterrows():
        # Use column indices since column names may be duplicated
        values = row.values.tolist()

        # Skip rows where the hotspot ID is empty (footer/notes)
        if len(values) <= COL_GOOGLE_MAP:
            continue

        hotspot_id = str(values[COL_HOTSPOT_ID]).strip() if pd.notna(values[COL_HOTSPOT_ID]) else ""
        if not hotspot_id or hotspot_id == "nan":
            continue

        # Skip if it looks like a footer/note row
        if hotspot_id in ("หมายเหตุ", "ที่มาของข้อมูล"):
            break

        province = str(values[COL_PROVINCE]).strip() if pd.notna(values[COL_PROVINCE]) else ""

        # Filter by province
        if province_filter and province != province_filter:
            continue

        # Extract Google Maps link, cleaning up any surrounding quotes
        google_map_raw = str(values[COL_GOOGLE_MAP]).strip() if pd.notna(values[COL_GOOGLE_MAP]) else ""
        google_map_link = google_map_raw.strip('"').strip("'")

        hotspot = {
            "hotspot_id": hotspot_id,
            "date_th": str(values[COL_DATE]).strip() if pd.notna(values[COL_DATE]) else "",
            "th_time": th_time,
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
        }
        hotspots.append(hotspot)

    return hotspots


def _nearby_times(base_time: str, spread: int = 5) -> list[str]:
    """
    Generate a list of 4-digit time strings around a base time.

    Tries the exact time first, then alternates ±1, ±2, ... up to ±spread.

    Args:
        base_time: 4-digit time string like "0200".
        spread: Maximum minutes to search in each direction.

    Returns:
        List of time strings to try, e.g. ["0200", "0159", "0201", ...].
    """
    h = int(base_time[:2])
    m = int(base_time[2:])
    base_minutes = h * 60 + m

    times = [base_time]  # try exact first
    for delta in range(1, spread + 1):
        for sign in (-1, +1):
            candidate = base_minutes + (sign * delta)
            # Wrap around midnight
            candidate = candidate % (24 * 60)
            ch, cm = divmod(candidate, 60)
            times.append(f"{ch:02d}{cm:02d}")

    return times


def _try_download_excel(
    sat_name: str,
    date_str: str,
    base_time: str,
    display_name: str,
    time_spread: int = 5,
) -> tuple[bytes | None, str]:
    """
    Try to download a GISTDA Excel file, searching nearby times if exact match fails.

    Args:
        sat_name: GISTDA satellite name (e.g. "N_Vi1").
        date_str: Thai date as "yyyymmdd".
        base_time: Base Thai time as "HHMM".
        display_name: Satellite display name for logging.
        time_spread: Minutes to search around base_time.

    Returns:
        Tuple of (file_content_bytes, matched_time) or (None, "").
    """
    candidate_times = _nearby_times(base_time, time_spread)

    for time_str in candidate_times:
        url = _build_excel_url(sat_name, date_str, time_str)

        try:
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                if time_str != base_time:
                    logger.info(
                        "Found Excel for %s at nearby time %s (base was %s)",
                        display_name, time_str, base_time,
                    )
                return response.content, time_str
            elif response.status_code != 404:
                logger.error(
                    "HTTP %d downloading Excel for %s time %s",
                    response.status_code, display_name, time_str,
                )
        except requests.exceptions.RequestException as e:
            logger.error(
                "Failed to download Excel for %s time %s: %s",
                display_name, time_str, e,
            )

    return None, ""


def _download_and_parse_single(
    sat_name: str,
    date_str: str,
    base_time: str,
    display_name: str,
    time_spread: int,
    province_filter: str,
    downloaded_files: set[str],
) -> list[dict]:
    """
    Download one Excel file (with fuzzy time matching), parse it, and return hotspots.

    Adds to downloaded_files set if successful.
    Returns empty list on failure or if the file was already downloaded.

    Args:
        sat_name: GISTDA satellite name (e.g. "N_Vi1" or "G_Vi1").
        date_str: Thai date as "yyyymmdd".
        base_time: Base Thai time as "HHMM".
        display_name: Satellite display name for logging and result dicts.
        time_spread: Minutes to search around base_time.
        province_filter: Province name to filter hotspots.
        downloaded_files: Set of already-downloaded file keys (mutated in place).

    Returns:
        List of hotspot dicts filtered by province.
    """
    content, matched_time = _try_download_excel(
        sat_name=sat_name,
        date_str=date_str,
        base_time=base_time,
        display_name=display_name,
        time_spread=time_spread,
    )

    if content is None:
        logger.warning(
            "No Excel found for %s %s_%s (tried ±%d min). Skipping.",
            display_name, date_str, base_time, time_spread,
        )
        return []

    # Skip if we already downloaded this exact file
    file_key = f"{sat_name}_{date_str}_{matched_time}"
    if file_key in downloaded_files:
        logger.info("Already downloaded %s, skipping.", file_key)
        return []
    downloaded_files.add(file_key)

    # Save to temp file and parse
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    logger.info(
        "Saved Excel to %s (%d bytes) — matched time: %s",
        tmp_path, len(content), matched_time,
    )

    hotspots = _parse_excel_sheet(
        filepath=tmp_path,
        province_filter=province_filter,
        sat_display_name=display_name,
        th_time=matched_time,
    )

    logger.info(
        "Parsed %d hotspots for %s in %s (time %s)",
        len(hotspots), province_filter, display_name, matched_time,
    )

    # Clean up temp file
    try:
        Path(tmp_path).unlink()
    except OSError:
        pass

    return hotspots


def download_and_parse_excel(
    pass_times: list,
    province_filter: str = "ลำพูน",
    time_spread: int = 5,
    gistda_time_spread: int = 10,
    gistda_folder_map: dict[str, tuple[str, str]] | None = None,
) -> tuple[list[dict], int]:
    """
    Download and parse GISTDA Excel files for each discovered pass time.

    Uses fuzzy time matching: if the exact FIRMS-reported time doesn't have
    a matching Excel file, tries ±time_spread minutes around it.

    For satellites that also exist in the GISTDA folder (specified by
    gistda_folder_map), an additional download is attempted from the
    GISTDA folder path (e.g. G_Vi1 instead of N_Vi1).

    Args:
        pass_times: List of PassTime objects from firms_api.discover_pass_times().
        province_filter: Province name to filter hotspots.
        time_spread: Minutes to search around each pass time (default 5).
        gistda_time_spread: Minutes to search around each pass time specifically
                            for GISTDA folder downloads (default 10).
        gistda_folder_map: Mapping from NASA sat name to (GISTDA sat name,
                           display name), e.g. {"N_Vi1": ("G_Vi1", "Suomi NPP - GISTDA")}.

    Returns:
        Tuple of (hotspot_list, files_downloaded_count).
    """
    all_hotspots: list[dict] = []
    downloaded_files: set[str] = set()  # track (sat_name, date, time) to avoid dupes

    for pt in pass_times:
        # 1. Download from NASA folder
        logger.info(
            "Downloading Excel (NASA folder): %s (%s, %s ±%dmin)",
            pt.display_name, pt.thai_date, pt.thai_time, time_spread,
        )

        hotspots = _download_and_parse_single(
            sat_name=pt.gistda_sat_name,
            date_str=pt.thai_date,
            base_time=pt.thai_time,
            display_name=pt.display_name,
            time_spread=time_spread,
            province_filter=province_filter,
            downloaded_files=downloaded_files,
        )
        all_hotspots.extend(hotspots)

        # 2. Download from GISTDA folder if this satellite has a GISTDA equivalent
        if gistda_folder_map and pt.gistda_sat_name in gistda_folder_map:
            g_sat_name, g_display_name = gistda_folder_map[pt.gistda_sat_name]

            logger.info(
                "Downloading Excel (GISTDA folder): %s (%s, %s ±%dmin)",
                g_display_name, pt.thai_date, pt.thai_time, gistda_time_spread,
            )

            g_hotspots = _download_and_parse_single(
                sat_name=g_sat_name,
                date_str=pt.thai_date,
                base_time=pt.thai_time,
                display_name=g_display_name,
                time_spread=gistda_time_spread,
                province_filter=province_filter,
                downloaded_files=downloaded_files,
            )
            all_hotspots.extend(g_hotspots)

    files_downloaded = len(downloaded_files)
    logger.info(
        "Total hotspots from all Excel files: %d (province: %s, files: %d)",
        len(all_hotspots), province_filter, files_downloaded,
    )

    return all_hotspots, files_downloaded
