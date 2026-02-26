#!/usr/bin/env python3
"""
Fetch hotspots from GISTDA API and print the formatted message.
Does NOT send to LINE — for preview/debug only.

Usage:
    python test_fetch.py
    python test_fetch.py --province 63   # override province
"""

import argparse
from config import Config
from hotspot_api import fetch_hotspots
from message_formatter import format_hotspot_message


def main():
    parser = argparse.ArgumentParser(description="Fetch & preview hotspot message")
    parser.add_argument("--province", type=int, help="Override province IDN")
    args = parser.parse_args()

    config = Config()
    province = args.province or config.PROVINCE_IDN

    print(f"🔍 Fetching hotspots for province {province}...")
    hotspots = fetch_hotspots(
        api_key=config.GISTDA_API_KEY,
        base_url=config.GISTDA_BASE_URL,
        province_idn=province,
        limit=config.FETCH_LIMIT,
    )
    print(f"📡 API returned {len(hotspots)} hotspots\n")

    if hotspots:
        print("━" * 60)
        print("RAW DATA (first 3):")
        print("━" * 60)
        for i, spot in enumerate(hotspots[:3], 1):
            print(f"\n--- Hotspot {i} ---")
            for key, val in spot.items():
                print(f"  {key}: {val}")
        if len(hotspots) > 3:
            print(f"\n  ... and {len(hotspots) - 3} more")

    print("\n" + "━" * 60)
    print("FORMATTED MESSAGE:")
    print("━" * 60)
    message = format_hotspot_message(hotspots, config.SCHEDULE_TIMES)
    print(message)
    print("━" * 60)
    print(f"📏 Message length: {len(message)} chars")


if __name__ == "__main__":
    main()
