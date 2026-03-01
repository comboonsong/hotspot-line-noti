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
) -> list[str]:
    """
    Format hotspot data into Thai notification message(s).

    If total hotspots >= 11, the message is separated into multiple bubbles:
      1) Header
      2) One bubble per satellite
      3) Ending
    Otherwise, returns a single combined string bubble.

    Args:
        hotspots: List of hotspot dicts from gistda_excel.download_and_parse_excel().
        schedule_times: List of scheduled time strings (currently unused but kept
                        for future use).
        now: Current datetime (defaults to now in Bangkok timezone).
        gistda_unavailable: True if FIRMS found passes but all GISTDA Excel
                            downloads failed.

    Returns:
        List of formatted Thai message strings (bubbles) to send.
    """
    if now is None:
        now = datetime.now(TZ_BANGKOK)

    today_str = _format_thai_date(now)
    current_time_str = f"{now.strftime('%H:%M')}น."

    # 1. Prepare Header
    header_lines = [
        "เรียน ผู้บริหารและผู้เกี่ยวข้อง",
        f"     สนง.ทสจ. ลำพูน ขอรายงานข้อมูลจุดความร้อน วันที่ {today_str}",
    ]

    # No hotspots scenario
    if not hotspots:
        start_time_str = "00:00น." if now.hour < 12 else "12:00น."
        base_no_hotspot = f"ไม่พบจุดความร้อนในพื้นที่จังหวัดลำพูน รอบ {start_time_str} ถึง {current_time_str}"
        
        if gistda_unavailable:
            header_lines.append(
                f"{base_no_hotspot} "
                f"(ไม่มีข้อมูลให้ดาวน์โหลดจาก GISTDA เวลา {current_time_str})"
            )
        else:
            header_lines.append(base_no_hotspot)
        header_lines.append("")
        header_lines.append("จึงเรียนมาเพื่อโปรดพิจารณา")
        return ["\n".join(header_lines)]

    # 2. Group by satellite_name, then by th_time
    # Structure: { satellite_name: { th_time: [hotspots] } }
    sat_groups: dict[str, dict[str, list[dict]]] = {}
    for spot in hotspots:
        sat_name = spot.get("satellite_name", "unknown")
        th_time = spot.get("th_time", "0000")
        
        if sat_name not in sat_groups:
            sat_groups[sat_name] = {}
        if th_time not in sat_groups[sat_name]:
            sat_groups[sat_name][th_time] = []
            
        sat_groups[sat_name][th_time].append(spot)

    # Sort satellites by SAT_ORDER
    sorted_sats = sorted(
        sat_groups.items(),
        key=lambda x: SAT_ORDER.get(x[0], 99)
    )

    should_separate = len(hotspots) >= 11
    bubbles: list[str] = []

    if should_separate:
        # Push header alone
        bubbles.append("\n".join(header_lines))
    else:
        # We will keep combining everything into header_lines
        pass

    # 3. Build text for each satellite
    combined_body_lines = []
    for satellite_name, time_groups in sorted_sats:
        sat_lines = []
        
        # Sort time groups chronologically
        sorted_times = sorted(time_groups.items(), key=lambda x: x[0])
        
        for th_time_raw, spots in sorted_times:
            th_time = _format_time(th_time_raw)
            group_count = len(spots)

            if not should_separate and len(combined_body_lines) > 0 or len(sat_lines) > 0:
                sat_lines.append("")
                
            sat_lines.append(
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
                sat_lines.append(f"ต.{sub_district} อ.{district} จำนวน {area_count} จุด")

                for spot in area_spots:
                    gmap_link = spot.get("google_maps_link", "")
                    land_use = spot.get("land_use", "")
                    sat_lines.append(f"{gmap_link} ({land_use})")
        
        if should_separate:
            # One complete bubble per satellite
            bubbles.append("\n".join(sat_lines))
        else:
            # Accumulate
            combined_body_lines.append("")
            combined_body_lines.extend(sat_lines)

    # 4. Prepare Ending
    ending_lines = ["\nจึงเรียนมาเพื่อโปรดพิจารณา"]

    if should_separate:
        bubbles.append("\n".join(ending_lines).strip())
        return bubbles
    else:
        # Combine Header + Body + Ending
        full_message_lines = header_lines + combined_body_lines + ending_lines
        return ["\n".join(full_message_lines)]
