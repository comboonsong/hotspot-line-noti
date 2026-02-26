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

# Thai confidence labels
CONFIDENCE_LABELS = {
    "nominal": "ปกติ",
    "low": "ต่ำ",
    "high": "สูง",
}

# Thailand timezone
TZ_BANGKOK = timezone(timedelta(hours=7))


def _format_thai_date(dt: datetime) -> str:
    """Format datetime to Thai date string, e.g. '23 ก.พ. 2569'."""
    thai_year = dt.year + BE_OFFSET
    return f"{dt.day} {THAI_MONTHS[dt.month]} {thai_year}"


def _format_time(time_str: str) -> str:
    """Format time string like '0637' or '1337' to 'HH:MMน.'."""
    if len(time_str) == 4 and time_str.isdigit():
        return f"{time_str[:2]}:{time_str[2:]}น."
    return time_str


def _get_confidence_label(confidence: str) -> str:
    """Get Thai label for confidence level."""
    return CONFIDENCE_LABELS.get(confidence.lower(), confidence)


def _get_time_range_str(now: datetime) -> str:
    """Get time range string from 00:00 today to current time."""
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start_str = f"{start.strftime('%H:%M')}น. {_format_thai_date(start)}"
    end_str = f"{now.strftime('%H:%M')}น. {_format_thai_date(now)}"
    return f"{start_str} — {end_str}"


def _get_next_check_time(schedule_times: list[str], now: datetime) -> str:
    """
    Determine the next scheduled check time.

    Args:
        schedule_times: List of time strings like ["06:00", "14:00"].
        now: Current datetime.

    Returns:
        Next check time string, e.g. "14:00น."
    """
    today_times = []
    for t in schedule_times:
        parts = t.strip().split(":")
        if len(parts) == 2:
            h, m = int(parts[0]), int(parts[1])
            check_dt = now.replace(hour=h, minute=m, second=0, microsecond=0)
            today_times.append((check_dt, t.strip()))

    # Sort by time
    today_times.sort(key=lambda x: x[0])

    # Find next time after now
    for check_dt, t_str in today_times:
        if check_dt > now:
            return f"{t_str}น."

    # If all times today have passed, next is tomorrow's first time
    if today_times:
        return f"{today_times[0][1]}น. (พรุ่งนี้)"

    return "—"


def format_hotspot_message(
    hotspots: list[dict],
    schedule_times: list[str],
    now: datetime | None = None,
) -> str:
    """
    Format hotspot data into a Thai notification message.

    Groups by (satellite_name, th_time), then by (sub_district, district).

    Args:
        hotspots: List of hotspot dicts from fetch_hotspots().
        schedule_times: List of scheduled time strings.
        now: Current datetime (defaults to now in Bangkok timezone).

    Returns:
        Formatted Thai message string.
    """
    if now is None:
        now = datetime.now(TZ_BANGKOK)

    today_str = _format_thai_date(now)

    # Header
    lines = [
        "เรียน ผู้บริหารและผู้เกี่ยวข้อง",
        f"     สนง.ทสจ. ลำพูน ขอรายงานข้อมูลจุดความร้อน วันที่ {today_str}",
    ]

    # No hotspots at all
    if not hotspots:
        lines.append("ไม่พบจุดความร้อนในพื้นที่จังหวัดลำพูน")
        lines.append("")
        lines.append("จึงเรียนมาเพื่อโปรดพิจารณา")
        return "\n".join(lines)

    # Filter only today's hotspots (using Thai date)
    today_date = now.strftime("%Y-%m-%d")
    today_hotspots = []
    for spot in hotspots:
        th_date = spot.get("th_date", "")
        if th_date.startswith(today_date):
            today_hotspots.append(spot)

    logger.info(
        "Filtered %d/%d hotspots for today (%s).",
        len(today_hotspots), len(hotspots), today_date,
    )

    # No hotspots today
    if not today_hotspots:
        lines.append("ไม่พบจุดความร้อนในพื้นที่จังหวัดลำพูน")
        lines.append("")
        lines.append("จึงเรียนมาเพื่อโปรดพิจารณา")
        return "\n".join(lines)

    # Group by (satellite_name, th_time)
    sat_time_groups: dict[tuple[str, str], list[dict]] = {}
    for spot in today_hotspots:
        key = (spot.get("satellite_name", "unknown"), spot.get("th_time", "0000"))
        sat_time_groups.setdefault(key, []).append(spot)

    # Sort priority for satellites: N (Suomi NPP) → N20 (NOAA-20) → N21 (NOAA-21)
    SAT_ORDER = {"Suomi NPP": 0, "NOAA-20": 1, "NOAA-21": 2}

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
