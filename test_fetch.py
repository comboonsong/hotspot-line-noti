#!/usr/bin/env python3
"""
Fetch hotspots via FIRMS → GISTDA Excel and print the formatted message.
Does NOT send to LINE — for preview/debug only.

Usage:
    python test_fetch.py
    python test_fetch.py --date 2026-02-26
    python test_fetch.py --date-range 2
"""

import argparse
from datetime import datetime

from config import Config
from firms_api import discover_pass_times, TZ_BANGKOK
from gistda_excel import download_and_parse_excel
from message_formatter import format_hotspot_message


def main():
    parser = argparse.ArgumentParser(
        description="Fetch & preview hotspot message (FIRMS → GISTDA Excel)"
    )
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="Override 'today' in YYYY-MM-DD format.",
    )
    parser.add_argument(
        "--date-range",
        type=int,
        default=2,
        help="FIRMS API date range in days (default: 2).",
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["satellite", "district", "both"],
        default="satellite",
        help="Message format: satellite (default), district, or both.",
    )
    args = parser.parse_args()

    config = Config()

    # Parse target date
    if args.date:
        today = datetime.strptime(args.date, "%Y-%m-%d").replace(
            hour=23, minute=59, tzinfo=TZ_BANGKOK
        )
    else:
        today = datetime.now(TZ_BANGKOK)

    print(f"🕐 Target date: {today.strftime('%Y-%m-%d')}")
    print(f"📡 FIRMS date range: {args.date_range} day(s)")
    print(f"🏔  Province filter: {config.PROVINCE_FILTER}")
    print(f"📝 Message mode: {args.mode}")
    print()

    # 1. Discover pass times
    print("🔍 Discovering satellite pass times from FIRMS...")
    pass_times = discover_pass_times(
        map_key=config.FIRMS_MAP_KEY,
        bbox=config.FIRMS_THA_BBOX,
        sources=config.FIRMS_SOURCES,
        firms_to_gistda=config.FIRMS_TO_GISTDA_SAT,
        sat_display=config.GISTDA_SAT_DISPLAY,
        today_date=today,
        date_range=args.date_range,
    )

    if pass_times:
        print(f"📡 Found {len(pass_times)} pass time(s):")
        for pt in pass_times:
            print(f"   {pt.display_name} | {pt.thai_date}_{pt.thai_time} | {pt.hotspot_count} hotspots")
    else:
        print("⚠️  No pass times found.")
    print()

    # 2. Download & parse Excel
    print("📥 Downloading GISTDA Excel files...")
    hotspots, files_downloaded = download_and_parse_excel(
        pass_times=pass_times,
        province_filter=config.PROVINCE_FILTER,
        time_spread=config.TIME_SPREAD,
        gistda_time_spread=config.GISTDA_TIME_SPREAD,
        gistda_folder_map=config.GISTDA_FOLDER_MAP,
    )
    print(f"📊 Parsed {len(hotspots)} hotspots for {config.PROVINCE_FILTER} ({files_downloaded} files)")

    if hotspots:
        print()
        print("━" * 60)
        print("RAW DATA (first 3):")
        print("━" * 60)
        for i, spot in enumerate(hotspots[:3], 1):
            print(f"\n--- Hotspot {i} ---")
            for key, val in spot.items():
                print(f"  {key}: {val}")
        if len(hotspots) > 3:
            print(f"\n  ... and {len(hotspots) - 3} more")

    # 3. Format message
    print("\n" + "━" * 60)
    print("FORMATTED MESSAGE:")
    print("━" * 60)
    messages = format_hotspot_message(hotspots, config.SCHEDULE_TIMES, today, mode=args.mode)
    for i, msg in enumerate(messages, 1):
        print(f"--- Bubble {i} ---")
        print(msg)
        print()
    print("━" * 60)
    print(f"📏 Total bubbles: {len(messages)}")


if __name__ == "__main__":
    main()
