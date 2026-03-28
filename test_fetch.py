#!/usr/bin/env python3
"""
Fetch hotspots via GISTDA directory API and print the formatted message.
Does NOT send to LINE — for preview/debug only.

Usage:
    python test_fetch.py
    python test_fetch.py --date 2026-02-26
    python test_fetch.py --mode district
"""

import argparse
from datetime import datetime, timezone, timedelta

from gistda_excel import TZ_BANGKOK, download_and_parse_excel
from message_formatter import format_hotspot_message
from config import Config


def main():
    parser = argparse.ArgumentParser(
        description="Fetch & preview hotspot message (GISTDA directory API)"
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
        help="Override time in HH:MM format (default: 23:59 if --date used, else current time).",
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
    parser.add_argument(
        "--mode",
        type=str,
        choices=["satellite", "district", "both"],
        default="satellite",
        help="Message format: satellite (default), district, or both.",
    )
    args = parser.parse_args()

    config = Config()

    # Parse target datetime
    if args.date:
        dt = datetime.strptime(args.date, "%Y-%m-%d")
        if args.time:
            h, m = map(int, args.time.split(":"))
            now = dt.replace(hour=h, minute=m, tzinfo=TZ_BANGKOK)
        else:
            now = dt.replace(hour=23, minute=59, tzinfo=TZ_BANGKOK)
    else:
        now = datetime.now(TZ_BANGKOK)

    print(f"🕐 Target date/time : {now.strftime('%Y-%m-%d %H:%M')} (ICT)")
    print(f"🏔  Province filter  : {config.PROVINCE_FILTER}")
    print(f"📝 Message mode     : {args.mode}")
    if args.window_start or args.window_end:
        print(f"🪟 Window           : {args.window_start or '00:00'} → {args.window_end or 'now'}")
    print()

    # 1. Download & parse
    print("📥 Fetching from GISTDA directory API...")
    hotspots, files_downloaded, latest_hotspot_time = download_and_parse_excel(
        now=now,
        province_filter=config.PROVINCE_FILTER,
        window_start=args.window_start,
        window_end=args.window_end,
    )
    print(f"📊 {len(hotspots)} hotspots for {config.PROVINCE_FILTER} ({files_downloaded} files)")
    print(f"⏱  Latest hotspot time: {latest_hotspot_time!r} {'→ จะบันทึกเป็น state ถัดไป' if latest_hotspot_time else '→ state ไม่เปลี่ยน'}")

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

    # 2. Format message
    print("\n" + "━" * 60)
    print("FORMATTED MESSAGE:")
    print("━" * 60)
    messages = format_hotspot_message(
        hotspots, config.SCHEDULE_TIMES, now,
        window_start=args.window_start,
        window_end=args.window_end,
        mode=args.mode,
    )
    for i, msg in enumerate(messages, 1):
        print(f"--- Bubble {i} ---")
        print(msg)
        print()
    print("━" * 60)
    print(f"📏 Total bubbles: {len(messages)}")


if __name__ == "__main__":
    main()
