#!/usr/bin/env python3
"""
Test script for the LINE Hotspot Notification Bot (GISTDA directory API protocol).
Tests file listing, Excel download/parsing, message formatting, and edge cases.

Usage:
    python test_bot.py                          # Test with today's date
    python test_bot.py --date 2026-02-26        # Test with a specific date
    python test_bot.py --date 2026-02-26 --time 14:00   # Test with specific time
"""

import argparse
from datetime import datetime

from config import Config
from gistda_excel import TZ_BANGKOK, list_today_files, download_and_parse_excel
from message_formatter import format_hotspot_message

SEPARATOR = "=" * 60


def _parse_now(date_str: str | None, time_str: str | None) -> datetime:
    """Parse --date/--time arguments or return current Thai time."""
    if date_str:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        if time_str:
            h, m = map(int, time_str.split(":"))
            return dt.replace(hour=h, minute=m, tzinfo=TZ_BANGKOK)
        else:
            return dt.replace(hour=23, minute=59, tzinfo=TZ_BANGKOK)
    return datetime.now(TZ_BANGKOK)


def test_file_listing(now: datetime):
    """Test GISTDA directory API file listing."""
    print(SEPARATOR)
    print("TEST 1: GISTDA Directory File Listing")
    print(SEPARATOR)
    print(f"  Target date: {now.strftime('%Y-%m-%d %H:%M')} (ICT)")
    print()

    files = list_today_files(today=now)

    if files:
        print(f"✅ Found {len(files)} file(s) for today:")
        for f in files:
            print(f"   {f['display_name']:25} | {f['filename']}")
    else:
        print("⚠️  No files found for today.")
    print()
    return files


def test_excel_download(config: Config, now: datetime, window_start: str = "", window_end: str = ""):
    """Test GISTDA Excel download and parsing."""
    print(SEPARATOR)
    print("TEST 2: Excel Download & Parse")
    print(SEPARATOR)

    hotspots, files_downloaded = download_and_parse_excel(
        now=now,
        province_filter=config.PROVINCE_FILTER,
        window_start=window_start,
        window_end=window_end,
    )

    if hotspots:
        print(f"✅ Parsed {len(hotspots)} hotspots for {config.PROVINCE_FILTER} ({files_downloaded} files):")
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


def test_message_formatting(hotspots, config: Config, now: datetime):
    """Test message formatting with real data."""
    print(SEPARATOR)
    print("TEST 3: Message Formatting")
    print(SEPARATOR)

    messages = format_hotspot_message(
        hotspots=hotspots,
        schedule_times=config.SCHEDULE_TIMES,
        now=now,
    )
    for i, msg in enumerate(messages, 1):
        print(f"--- Bubble {i} ---")
        print(msg)
        print()
    print(f"\n📏 Total bubbles: {len(messages)}")
    print()


def test_message_no_hotspots(config: Config, now: datetime):
    """Test message formatting with no hotspots."""
    print(SEPARATOR)
    print("TEST 4: Message with No Hotspots")
    print(SEPARATOR)

    messages = format_hotspot_message(
        hotspots=[],
        schedule_times=config.SCHEDULE_TIMES,
        now=now,
    )
    for i, msg in enumerate(messages, 1):
        print(f"--- Bubble {i} ---")
        print(msg)
        print()


def test_message_with_sample_data(config: Config, now: datetime):
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
            "nearest_village": "บ้านแวนนาริน",
            "distance_km": "3.50",
            "direction": "W",
            "google_maps_link": "http://maps.google.com/maps?q=18.18339,98.97259",
            "satellite_name": "Suomi NPP",
        },
        {
            "hotspot_id": "GG1202602261901w5nq8u2gd4",
            "date_th": "26 กุมภาพันธ์ 2026",
            "th_time": "0201",
            "sub_district_th": "ศรีวิชัย",
            "district_th": "ลี้",
            "province_th": "ลำพูน",
            "responsible_area": "ป่าอนุรักษ์",
            "nearest_village": "บ้านห้วยเรือนแม่เอิบ",
            "distance_km": "3.87",
            "direction": "NW",
            "google_maps_link": "http://maps.google.com/maps?q=18.04154,98.82314",
            "satellite_name": "Suomi NPP - GISTDA",
        },
        {
            "hotspot_id": "VG2202602261337x7abc12345",
            "date_th": "26 กุมภาพันธ์ 2026",
            "th_time": "2037",
            "sub_district_th": "แม่ตืน",
            "district_th": "ลี้",
            "province_th": "ลำพูน",
            "responsible_area": "ป่าสงวนแห่งชาติ",
            "nearest_village": "บ้านแม่ตืน",
            "distance_km": "2.10",
            "direction": "N",
            "google_maps_link": "http://maps.google.com/maps?q=18.0390,98.9500",
            "satellite_name": "NOAA-20",
        },
    ]

    messages = format_hotspot_message(
        hotspots=sample,
        schedule_times=config.SCHEDULE_TIMES,
        now=now,
    )
    for i, msg in enumerate(messages, 1):
        print(f"--- Bubble {i} ---")
        print(msg)
        print()
    print(f"\n📏 Total bubbles: {len(messages)}")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Test the GISTDA directory API hotspot notification pipeline."
    )
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="Override 'today' in YYYY-MM-DD format (default: current Thai date).",
    )
    parser.add_argument(
        "--time",
        type=str,
        default=None,
        help="Override time in HH:MM format.",
    )
    parser.add_argument(
        "--window-start",
        type=str,
        default="",
        help="Window start time HH:MM (e.g. '00:00'). Empty = no lower bound.",
    )
    parser.add_argument(
        "--window-end",
        type=str,
        default="",
        help="Window end time HH:MM (e.g. '05:25'). Empty = current time.",
    )
    args = parser.parse_args()

    config = Config()
    now = _parse_now(args.date, args.time)

    print(f"\n🕐 Target date/time: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🏔  Province filter : {config.PROVINCE_FILTER}")
    if args.window_start or args.window_end:
        print(f"🪟 Window          : {args.window_start or '00:00'} → {args.window_end or 'now'}")
    print()

    # Test 1: File listing
    test_file_listing(now)

    # Test 2: Download & parse
    hotspots = test_excel_download(config, now, args.window_start, args.window_end)

    # Test 3: Message formatting with real data
    test_message_formatting(hotspots, config, now)

    # Test 4: No hotspots
    test_message_no_hotspots(config, now)

    # Test 5: Sample data
    test_message_with_sample_data(config, now)

    print(SEPARATOR)
    print("✅ All tests completed!")
    print(SEPARATOR)


if __name__ == "__main__":
    main()
