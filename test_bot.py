#!/usr/bin/env python3
"""
Test script for the LINE Hotspot Notification Bot (FIRMS → GISTDA Excel protocol).
Tests FIRMS discovery, Excel download/parsing, message formatting, and edge cases.

Usage:
    python test_bot.py                          # Test with today's date
    python test_bot.py --date 2026-02-26        # Test with a specific date
    python test_bot.py --date-range 2           # Query FIRMS for 2 days
"""

import argparse
from datetime import datetime, timezone, timedelta

from config import Config
from firms_api import discover_pass_times, TZ_BANGKOK
from gistda_excel import download_and_parse_excel
from message_formatter import format_hotspot_message

SEPARATOR = "=" * 60


def _parse_today(date_str: str | None) -> datetime:
    """Parse --date argument or return current Thai time."""
    if date_str:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        # Set to end of day so all pass times on that date are included
        return dt.replace(hour=23, minute=59, tzinfo=TZ_BANGKOK)
    return datetime.now(TZ_BANGKOK)


def test_firms_discovery(config: Config, today: datetime, date_range: int):
    """Test FIRMS API pass time discovery."""
    print(SEPARATOR)
    print("TEST 1: FIRMS Pass Time Discovery")
    print(SEPARATOR)
    print(f"  Target date: {today.strftime('%Y-%m-%d')}")
    print(f"  Date range: {date_range} day(s)")
    print()

    pass_times = discover_pass_times(
        map_key=config.FIRMS_MAP_KEY,
        bbox=config.FIRMS_THA_BBOX,
        sources=config.FIRMS_SOURCES,
        firms_to_gistda=config.FIRMS_TO_GISTDA_SAT,
        sat_display=config.GISTDA_SAT_DISPLAY,
        today_date=today,
        date_range=date_range,
    )

    if pass_times:
        print(f"✅ Discovered {len(pass_times)} pass time(s):")
        for pt in pass_times:
            print(
                f"   {pt.display_name} | date={pt.thai_date} "
                f"time={pt.thai_time} | {pt.hotspot_count} hotspots"
            )
    else:
        print("⚠️  No pass times found for today.")
    print()
    return pass_times


def test_excel_download(pass_times, config: Config):
    """Test GISTDA Excel download and parsing."""
    print(SEPARATOR)
    print("TEST 2: GISTDA Excel Download & Parse")
    print(SEPARATOR)

    if not pass_times:
        print("⚠️  No pass times to test — skipping Excel download.")
        print()
        return []

    hotspots, files_downloaded = download_and_parse_excel(
        pass_times=pass_times,
        province_filter=config.PROVINCE_FILTER,
    )

    if hotspots:
        print(f"✅ Parsed {len(hotspots)} hotspots for {config.PROVINCE_FILTER}:")
        for i, spot in enumerate(hotspots[:5], 1):
            print(f"\n   --- Hotspot {i} ---")
            for key, val in spot.items():
                print(f"     {key}: {val}")
        if len(hotspots) > 5:
            print(f"\n   ... and {len(hotspots) - 5} more")
    else:
        print(f"⚠️  No hotspots found for {config.PROVINCE_FILTER}.")
    print()
    return hotspots


def test_message_formatting(hotspots, config: Config, today: datetime):
    """Test message formatting with real data."""
    print(SEPARATOR)
    print("TEST 3: Message Formatting")
    print(SEPARATOR)

    message = format_hotspot_message(
        hotspots=hotspots,
        schedule_times=config.SCHEDULE_TIMES,
        now=today,
    )
    print(message)
    print(f"\n📏 Message length: {len(message)} chars")
    print()


def test_message_no_hotspots(config: Config, today: datetime):
    """Test message formatting with no hotspots."""
    print(SEPARATOR)
    print("TEST 4: Message with No Hotspots")
    print(SEPARATOR)

    message = format_hotspot_message(
        hotspots=[],
        schedule_times=config.SCHEDULE_TIMES,
        now=today,
    )
    print(message)
    print()


def test_message_with_sample_data(config: Config, today: datetime):
    """Test message formatting with sample Excel-like data."""
    print(SEPARATOR)
    print("TEST 5: Message with Sample Data")
    print(SEPARATOR)

    sample = [
        {
            "hotspot_id": "VG1202602261901w5nq8u2gd4",
            "date_th": "26 กุมภาพันธ์ 2026",
            "th_time": "0201",
            "sub_district_th": "ศรีวิชัย",
            "district_th": "ลี้",
            "province_th": "ลำพูน",
            "responsible_area": "ป่าอนุรักษ์",
            "land_use": "พื้นที่ป่า",
            "nearest_village": "บ้านห้วยเรือนแม่เอิบ",
            "distance_km": "3.87",
            "direction": "NW",
            "google_maps_link": "http://maps.google.com/maps?q=18.04154,98.82314",
            "satellite_name": "Suomi NPP",
        },
        {
            "hotspot_id": "VG1202602261901w5nrknjtut",
            "date_th": "26 กุมภาพันธ์ 2026",
            "th_time": "0201",
            "sub_district_th": "ป่าพลู",
            "district_th": "บ้านโฮ่ง",
            "province_th": "ลำพูน",
            "responsible_area": "ป่าสงวนแห่งชาติ",
            "land_use": "พื้นที่ป่า",
            "nearest_village": "บ้านแวนนาริน",
            "distance_km": "3.50",
            "direction": "W",
            "google_maps_link": "http://maps.google.com/maps?q=18.18339,98.97259",
            "satellite_name": "Suomi NPP",
        },
        {
            "hotspot_id": "VG1202602261901w5nr7rhg84",
            "date_th": "26 กุมภาพันธ์ 2026",
            "th_time": "0201",
            "sub_district_th": "ป่าพลู",
            "district_th": "บ้านโฮ่ง",
            "province_th": "ลำพูน",
            "responsible_area": "ป่าสงวนแห่งชาติ",
            "land_use": "พื้นที่ป่า",
            "nearest_village": "บ้านห้วยฮ่อมใน",
            "distance_km": "5.74",
            "direction": "SW",
            "google_maps_link": "http://maps.google.com/maps?q=18.18848,98.93841",
            "satellite_name": "Suomi NPP",
        },
        {
            "hotspot_id": "VG2202602261337x7abc12345",
            "date_th": "26 กุมภาพันธ์ 2026",
            "th_time": "2037",
            "sub_district_th": "แม่ตืน",
            "district_th": "ลี้",
            "province_th": "ลำพูน",
            "responsible_area": "ป่าสงวนแห่งชาติ",
            "land_use": "พื้นที่ป่า",
            "nearest_village": "บ้านแม่ตืน",
            "distance_km": "2.10",
            "direction": "N",
            "google_maps_link": "http://maps.google.com/maps?q=18.0390,98.9500",
            "satellite_name": "NOAA-20",
        },
    ]

    message = format_hotspot_message(
        hotspots=sample,
        schedule_times=config.SCHEDULE_TIMES,
        now=today,
    )
    print(message)
    print(f"\n📏 Message length: {len(message)} chars")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Test the FIRMS → GISTDA Excel hotspot notification pipeline."
    )
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="Override 'today' in YYYY-MM-DD format (default: current Thai date).",
    )
    parser.add_argument(
        "--date-range",
        type=int,
        default=2,
        help="FIRMS API date range in days (default: 1).",
    )
    args = parser.parse_args()

    config = Config()
    today = _parse_today(args.date)

    print(f"\n🕐 Target date: {today.strftime('%Y-%m-%d')}")
    print(f"📡 FIRMS date range: {args.date_range} day(s)")
    print(f"🏔  Province filter: {config.PROVINCE_FILTER}")
    print()

    # Test 1: FIRMS discovery
    pass_times = test_firms_discovery(config, today, args.date_range)

    # Test 2: Excel download & parse
    hotspots = test_excel_download(pass_times, config)

    # Test 3: Message formatting with real data
    test_message_formatting(hotspots, config, today)

    # Test 4: No hotspots
    test_message_no_hotspots(config, today)

    # Test 5: Sample data
    test_message_with_sample_data(config, today)

    print(SEPARATOR)
    print("✅ All tests completed!")
    print(SEPARATOR)


if __name__ == "__main__":
    main()
