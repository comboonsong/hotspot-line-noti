"""
Message formatter for LINE hotspot notifications.

Formats hotspot data (from GISTDA Excel) into Thai notification messages.
"""

import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

# Thai Buddhist Era offset
BE_OFFSET = 543

# Thai month abbreviations
THAI_MONTHS = [
    "", "ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.",
    "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค.",
]

# Thailand timezone
TZ_BANGKOK = timezone(timedelta(hours=7))

# Satellite display order
SAT_ORDER = {"Suomi NPP": 0, "Suomi NPP - GISTDA": 1, "NOAA-20": 2, "NOAA-21": 3}


def _format_thai_date(dt: datetime) -> str:
    """Format datetime to Thai date string, e.g. '23 ก.พ. 2569'."""
    thai_year = dt.year + BE_OFFSET
    return f"{dt.day} {THAI_MONTHS[dt.month]} {thai_year}"


def _format_time(time_str: str) -> str:
    """Format time string like '0637' or '1337' to 'HH:MMน.'."""
    if len(time_str) == 4 and time_str.isdigit():
        return f"{time_str[:2]}:{time_str[2:]}น."
    return time_str


def format_hotspot_message(
    hotspots: list[dict],
    schedule_times: list[str],
    now: datetime | None = None,
    gistda_unavailable: bool = False,
) -> str:
    """
    Format hotspot data into a Thai notification message.

    Groups by (satellite_name, th_time), then by (sub_district, district).

    Args:
        hotspots: List of hotspot dicts from gistda_excel.download_and_parse_excel().
        schedule_times: List of scheduled time strings (currently unused but kept
                        for future use).
        now: Current datetime (defaults to now in Bangkok timezone).
        gistda_unavailable: True if FIRMS found passes but all GISTDA Excel
                            downloads failed.

    Returns:
        Formatted Thai message string.
    """
    if now is None:
        now = datetime.now(TZ_BANGKOK)

    today_str = _format_thai_date(now)
    current_time_str = f"{now.strftime('%H:%M')}น."

    # Header
    lines = [
        "เรียน ผู้บริหารและผู้เกี่ยวข้อง",
        f"     สนง.ทสจ. ลำพูน ขอรายงานข้อมูลจุดความร้อน วันที่ {today_str}",
    ]

    # No hotspots
    if not hotspots:
        start_time_str = "00:00น." if now.hour < 12 else "12:00น."
        base_no_hotspot = f"ไม่พบจุดความร้อนในพื้นที่จังหวัดลำพูน รอบ {start_time_str} ถึง {current_time_str}"
        
        if gistda_unavailable:
            lines.append(
                f"{base_no_hotspot} "
                f"(ไม่มีข้อมูลให้ดาวน์โหลดจาก GISTDA เวลา {current_time_str})"
            )
        else:
            lines.append(base_no_hotspot)
        lines.append("")
        lines.append("จึงเรียนมาเพื่อโปรดพิจารณา")
        return "\n".join(lines)

    # Group by (satellite_name, th_time)
    sat_time_groups: dict[tuple[str, str], list[dict]] = {}
    for spot in hotspots:
        key = (spot.get("satellite_name", "unknown"), spot.get("th_time", "0000"))
        sat_time_groups.setdefault(key, []).append(spot)

    # Sort groups by th_time first, then satellite order
    sorted_groups = sorted(
        sat_time_groups.items(),
        key=lambda x: (x[0][1], SAT_ORDER.get(x[0][0], 99)),
    )

    for (satellite_name, th_time_raw), spots in sorted_groups:
        th_time = _format_time(th_time_raw)
        group_count = len(spots)

        lines.append("")
        lines.append(
            f"พบจุดความร้อนจากดาวเทียม {satellite_name} ระบบ VIIRS "
            f"รอบเวลา {th_time} จำนวน {group_count} จุด ดังนี้"
        )

        # Sub-group by (sub_district_th, district_th)
        area_groups: dict[tuple[str, str], list[dict]] = {}
        for spot in spots:
            area_key = (spot.get("sub_district_th", ""), spot.get("district_th", ""))
            area_groups.setdefault(area_key, []).append(spot)

        for (sub_district, district), area_spots in area_groups.items():
            area_count = len(area_spots)
            lines.append(f"ต.{sub_district} อ.{district} จำนวน {area_count} จุด")

            for spot in area_spots:
                gmap_link = spot.get("google_maps_link", "")
                land_use = spot.get("land_use", "")
                lines.append(f"{gmap_link} ({land_use})")

    lines.append("")
    lines.append("จึงเรียนมาเพื่อโปรดพิจารณา")

    return "\n".join(lines)
