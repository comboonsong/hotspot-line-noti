"""
Message formatter for LINE hotspot notifications.

Formats hotspot data (from GISTDA Excel) into Thai notification messages.
Produces two views:
  1) Grouped by satellite source (แบ่งตามแหล่งข้อมูล)
  2) Grouped by district (แบ่งตามอำเภอ)
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

# Maximum hotspots per bubble in satellite-based format
MAX_HOTSPOTS_PER_BUBBLE = 40

# Section separators
SEP_BY_SOURCE = (
    "\n"
    "\n"
    "📡 แบ่งตามแหล่งข้อมูล 📡\n"
    "\n"
    "\n"
)
SEP_BY_DISTRICT = (
    "\n"
    "\n"
    "🏘️ แบ่งตามอำเภอ 🏘️\n"
    "\n"
    "\n"
)


def _format_thai_date(dt: datetime) -> str:
    """Format datetime to Thai date string, e.g. '23 ก.พ. 2569'."""
    thai_year = dt.year + BE_OFFSET
    return f"{dt.day} {THAI_MONTHS[dt.month]} {thai_year}"


def _format_time(time_str: str) -> str:
    """Format time string like '0637' or '1337' to 'HH:MMน.'."""
    if len(time_str) == 4 and time_str.isdigit():
        return f"{time_str[:2]}:{time_str[2:]}น."
    return time_str


# ---------------------------------------------------------------------------
# Satellite-based format (แบ่งตามแหล่งข้อมูล)
# ---------------------------------------------------------------------------

def _format_by_satellite(hotspots: list[dict], should_separate: bool) -> list[str]:
    """
    Format hotspots grouped by satellite → time → area.

    Returns content-only bubbles (no header / ending).

    When should_separate is True:
      - Each satellite + time combination starts a new bubble.
      - Each bubble contains at most MAX_HOTSPOTS_PER_BUBBLE hotspots.
      - If a sub-district is split across bubbles, a "(ต่อ)" marker is added.
    When should_separate is False:
      - All hotspots are combined into one bubble.
    """
    # Group: { satellite_name: { th_time: [hotspots] } }
    sat_groups: dict[str, dict[str, list[dict]]] = {}
    for spot in hotspots:
        sat_name = spot.get("satellite_name", "unknown")
        th_time = spot.get("th_time", "0000")
        sat_groups.setdefault(sat_name, {}).setdefault(th_time, []).append(spot)

    # Sort satellites by SAT_ORDER
    sorted_sats = sorted(sat_groups.items(), key=lambda x: SAT_ORDER.get(x[0], 99))

    bubbles: list[str] = []
    combined_lines: list[str] = []

    for satellite_name, time_groups in sorted_sats:
        # Sort time groups chronologically
        for th_time_raw, spots in sorted(time_groups.items()):
            th_time = _format_time(th_time_raw)

            intro_line = (
                f"พบจุดความร้อนจากดาวเทียม {satellite_name} ระบบ VIIRS "
                f"รอบเวลา {th_time} จำนวน {len(spots)} จุด ดังนี้"
            )

            if should_separate:
                # Each satellite+time → new set of bubbles with 40-hotspot limit
                current_lines: list[str] = [intro_line]
                hotspot_count = 0

                # Sub-group by (sub_district, district)
                area_groups: dict[tuple[str, str], list[dict]] = {}
                for spot in spots:
                    key = (spot.get("sub_district_th", ""), spot.get("district_th", ""))
                    area_groups.setdefault(key, []).append(spot)

                for (sub_district, district), area_spots in area_groups.items():
                    for i, spot in enumerate(area_spots):
                        # Check limit before adding each hotspot
                        if hotspot_count >= MAX_HOTSPOTS_PER_BUBBLE:
                            # Preview line when splitting mid-sub-district
                            if i > 0:
                                remaining = len(area_spots) - i
                                current_lines.append(
                                    f"ต.{sub_district} อ.{district} "
                                    f"จุดความร้อน {remaining} จุด ที่เหลือระบุในข้อความถัดไป"
                                )
                            bubbles.append("\n".join(current_lines))
                            current_lines = []
                            hotspot_count = 0

                        # Add sub-district header when needed
                        if i == 0:
                            current_lines.append(
                                f"ต.{sub_district} อ.{district} จำนวน {len(area_spots)} จุด"
                            )
                        elif hotspot_count == 0:
                            # Continuation after bubble split
                            remaining = len(area_spots) - i
                            current_lines.append(
                                f"ต.{sub_district} อ.{district} (ต่อ) จำนวน {remaining} จุด"
                            )

                        gmap = spot.get("google_maps_link", "")
                        area = spot.get("responsible_area", "")
                        current_lines.append(f"{gmap} ({area})")
                        hotspot_count += 1

                if current_lines:
                    bubbles.append("\n".join(current_lines))
            else:
                # Not separated: combine into one bubble
                sat_lines: list[str] = []
                if combined_lines:
                    combined_lines.append("")

                sat_lines.append(intro_line)

                area_groups: dict[tuple[str, str], list[dict]] = {}
                for spot in spots:
                    key = (spot.get("sub_district_th", ""), spot.get("district_th", ""))
                    area_groups.setdefault(key, []).append(spot)

                for (sub_district, district), area_spots in area_groups.items():
                    sat_lines.append(f"ต.{sub_district} อ.{district} จำนวน {len(area_spots)} จุด")
                    for spot in area_spots:
                        gmap = spot.get("google_maps_link", "")
                        area = spot.get("responsible_area", "")
                        sat_lines.append(f"{gmap} ({area})")

                combined_lines.extend(sat_lines)

    if not should_separate:
        return ["\n".join(combined_lines)] if combined_lines else []
    return bubbles


# ---------------------------------------------------------------------------
# District-based format (แบ่งตามอำเภอ)
# ---------------------------------------------------------------------------

def _format_by_district(hotspots: list[dict], should_separate: bool) -> list[str]:
    """
    Format hotspots grouped by district → sub-district.

    Each hotspot line includes land_use, time, and satellite name.
    Districts are sorted by total hotspot count descending.
    Sub-districts within each district are also sorted by count descending.

    Returns content-only bubbles (no header / ending).
    If should_separate, one bubble per district; otherwise one combined bubble.
    """
    # Group: { district: { sub_district: [hotspots] } }
    district_groups: dict[str, dict[str, list[dict]]] = {}
    for spot in hotspots:
        district = spot.get("district_th", "")
        sub_district = spot.get("sub_district_th", "")
        district_groups.setdefault(district, {}).setdefault(sub_district, []).append(spot)

    # Sort districts by total count descending
    sorted_districts = sorted(
        district_groups.items(),
        key=lambda x: sum(len(spots) for spots in x[1].values()),
        reverse=True,
    )

    bubbles: list[str] = []
    combined_lines: list[str] = []

    for district, sub_groups in sorted_districts:
        district_total = sum(len(spots) for spots in sub_groups.values())
        dist_lines: list[str] = [
            f"อ.{district} พบจุดความร้อนทั้งหมด {district_total} จุด",
        ]

        # Sort sub-districts by count descending
        sorted_subs = sorted(
            sub_groups.items(),
            key=lambda x: len(x[1]),
            reverse=True,
        )

        for sub_district, spots in sorted_subs:
            dist_lines.append(f"ต.{sub_district} จำนวน {len(spots)} จุด")

            # Sort spots by time then satellite for consistent ordering
            sorted_spots = sorted(
                spots,
                key=lambda s: (
                    s.get("th_time", "0000"),
                    SAT_ORDER.get(s.get("satellite_name", ""), 99),
                ),
            )

            for spot in sorted_spots:
                gmap = spot.get("google_maps_link", "")
                area = spot.get("responsible_area", "")
                th_time = _format_time(spot.get("th_time", "0000"))
                sat_name = spot.get("satellite_name", "")
                dist_lines.append(f"{gmap} ({area}, รอบเวลา {th_time} ดาวเทียม {sat_name})")

        if should_separate:
            bubbles.append("\n".join(dist_lines))
        else:
            if combined_lines:
                combined_lines.append("")
            combined_lines.extend(dist_lines)

    if not should_separate:
        return ["\n".join(combined_lines)] if combined_lines else []
    return bubbles


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def format_hotspot_message(
    hotspots: list[dict],
    schedule_times: list[str],
    now: datetime | None = None,
    gistda_unavailable: bool = False,
    mode: str = "satellite",
) -> list[str]:
    """
    Format hotspot data into Thai notification messages.

    Args:
        hotspots: List of hotspot dicts from gistda_excel.
        schedule_times: Scheduled time strings (reserved for future use).
        now: Current datetime (defaults to now in Bangkok timezone).
        gistda_unavailable: True when FIRMS found passes but all downloads failed.
        mode: Output format — "satellite" (by source, default),
              "district" (by district), or "both" (satellite + district).

    Returns:
        List of formatted Thai message strings (bubbles) to send.
    """
    if now is None:
        now = datetime.now(TZ_BANGKOK)

    today_str = _format_thai_date(now)
    current_time_str = f"{now.strftime('%H:%M')}น."

    # Headers
    header_sat = (
        "เรียน ผู้บริหารและผู้เกี่ยวข้อง\n"
        f"     สนง.ทสจ. ลำพูน ขอรายงานข้อมูลจุดความร้อน วันที่ {today_str}"
    )
    header_dist = (
        "เรียน ผู้บริหารและผู้เกี่ยวข้อง\n"
        f"     สนง.ทสจ. ลำพูน ขอรายงานข้อมูลจุดความร้อน วันที่ {today_str} "
        "โดยมีอำเภอที่พบจุดความร้อนจากดาวเทียมระบบ VIIRS ดังนี้"
    )
    ending = "จึงเรียนมาเพื่อโปรดพิจารณา"

    # No hotspots scenario
    if not hotspots:
        start_time_str = "00:00น." if now.hour < 12 else "12:00น."
        base = f"ไม่พบจุดความร้อนในพื้นที่จังหวัดลำพูน รอบ {start_time_str} ถึง {current_time_str}"
        if gistda_unavailable:
            base += f" (ไม่มีข้อมูลให้ดาวน์โหลดจาก GISTDA เวลา {current_time_str})"
        return [f"{header_sat}\n{base}\n\n{ending}"]

    should_separate = len(hotspots) >= 11

    include_sat = mode in ("satellite", "both")
    include_dist = mode in ("district", "both")

    all_bubbles: list[str] = []

    if should_separate:
        if include_sat:
            sat_bubbles = _format_by_satellite(hotspots, should_separate)
            if include_dist:
                all_bubbles.append(SEP_BY_SOURCE)
            all_bubbles.append(header_sat)
            # Append ending to the last content bubble
            if sat_bubbles:
                sat_bubbles[-1] += f"\n\n{ending}"
            all_bubbles.extend(sat_bubbles)

        if include_dist:
            dist_bubbles = _format_by_district(hotspots, should_separate)
            if include_sat:
                all_bubbles.append(SEP_BY_DISTRICT)
            all_bubbles.append(header_dist)
            all_bubbles.extend(dist_bubbles)
            all_bubbles.append(ending)
    else:
        if include_sat:
            sat_bubbles = _format_by_satellite(hotspots, should_separate)
            parts_sat = []
            if include_dist:
                parts_sat.extend([SEP_BY_SOURCE, ""])
            parts_sat.append(header_sat)
            parts_sat.extend(sat_bubbles)
            parts_sat.append(f"\n{ending}")
            all_bubbles.append("\n".join(parts_sat))

        if include_dist:
            dist_bubbles = _format_by_district(hotspots, should_separate)
            parts_dist = []
            if include_sat:
                parts_dist.extend([SEP_BY_DISTRICT, ""])
            parts_dist.append(header_dist)
            parts_dist.extend(dist_bubbles)
            parts_dist.append(f"\n{ending}")
            all_bubbles.append("\n".join(parts_dist))

    return all_bubbles
