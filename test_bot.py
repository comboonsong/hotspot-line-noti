#!/usr/bin/env python3
"""
Test script for the LINE Hotspot Notification Bot.
Tests API fetching, message formatting, and edge cases.

Usage:
    python test_bot.py
"""

from datetime import datetime, timezone, timedelta
from hotspot_api import fetch_hotspots
from message_formatter import format_hotspot_message
from config import Config

TZ_BANGKOK = timezone(timedelta(hours=7))


def test_api_fetch():
    """Test fetching hotspots from the GISTDA API."""
    print("=" * 60)
    print("TEST 1: API Fetch")
    print("=" * 60)

    config = Config()
    hotspots = fetch_hotspots(
        api_key=config.GISTDA_API_KEY,
        base_url=config.GISTDA_BASE_URL,
        province_idn=config.PROVINCE_IDN,
        limit=config.FETCH_LIMIT,
    )
    print(f"✅ Fetched {len(hotspots)} hotspots")
    if hotspots:
        print(f"   Sample: {hotspots[0]}")
    print()


def test_message_with_hotspots():
    """Test message formatting with sample hotspot data."""
    print("=" * 60)
    print("TEST 2: Message with hotspots (multiple satellites & times)")
    print("=" * 60)

    now = datetime.now(TZ_BANGKOK)
    today = now.strftime("%Y-%m-%dT00:00:00")

    sample = [
        {
            "satellite_name": "Suomi NPP", "th_time": "0637",
            "sub_district_th": "แม่ตืน", "district_th": "ลี้",
            "google_maps_link": "http://maps.google.com/maps?q=18.0390,98.9500",
            "land_use": "ป่าสงวนแห่งชาติ", "acq_date": today, "province_th": "ลำพูน",
        },
        {
            "satellite_name": "NOAA-21", "th_time": "1337",
            "sub_district_th": "แม่ตืน", "district_th": "ลี้",
            "google_maps_link": "http://maps.google.com/maps?q=18.0385,98.9493",
            "land_use": "ป่าสงวนแห่งชาติ", "acq_date": today, "province_th": "ลำพูน",
        },
        {
            "satellite_name": "NOAA-21", "th_time": "1337",
            "sub_district_th": "แม่ตืน", "district_th": "ลี้",
            "google_maps_link": "http://maps.google.com/maps?q=18.0400,98.9510",
            "land_use": "พื้นที่เกษตรกรรม", "acq_date": today, "province_th": "ลำพูน",
        },
        {
            "satellite_name": "NOAA-21", "th_time": "1337",
            "sub_district_th": "ศรีวิชัย", "district_th": "ลี้",
            "google_maps_link": "http://maps.google.com/maps?q=18.0500,98.9600",
            "land_use": "ป่าสงวนแห่งชาติ", "acq_date": today, "province_th": "ลำพูน",
        },
        {
            "satellite_name": "NOAA-20", "th_time": "1405",
            "sub_district_th": "หนองหนาม", "district_th": "เมืองลำพูน",
            "google_maps_link": "http://maps.google.com/maps?q=18.5012,99.0234",
            "land_use": "พื้นที่เกษตรกรรม", "acq_date": today, "province_th": "ลำพูน",
        },
    ]

    message = format_hotspot_message(sample, ["06:00", "14:00"], now)
    print(message)
    print(f"\n📏 Message length: {len(message)} chars")
    print()


def test_message_no_hotspots():
    """Test message formatting with no hotspots."""
    print("=" * 60)
    print("TEST 3: No hotspots")
    print("=" * 60)

    now = datetime.now(TZ_BANGKOK)
    message = format_hotspot_message([], ["06:00", "14:00"], now)
    print(message)
    print()


def test_message_yesterday_only():
    """Test that yesterday's hotspots are filtered out."""
    print("=" * 60)
    print("TEST 4: Only yesterday's hotspots (should show 'ไม่พบ')")
    print("=" * 60)

    now = datetime.now(TZ_BANGKOK)
    yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%dT00:00:00")

    sample = [
        {
            "satellite_name": "NOAA-21", "th_time": "1337",
            "sub_district_th": "แม่ตืน", "district_th": "ลี้",
            "google_maps_link": "http://maps.google.com/maps?q=18.0385,98.9493",
            "land_use": "ป่าสงวนแห่งชาติ", "acq_date": yesterday, "province_th": "ลำพูน",
        },
    ]

    message = format_hotspot_message(sample, ["06:00", "14:00"], now)
    print(message)
    print()


def test_real_data():
    """Test with real API data and message formatting."""
    print("=" * 60)
    print("TEST 5: Real API data → formatted message")
    print("=" * 60)

    config = Config()
    hotspots = fetch_hotspots(
        api_key=config.GISTDA_API_KEY,
        base_url=config.GISTDA_BASE_URL,
        province_idn=config.PROVINCE_IDN,
        limit=config.FETCH_LIMIT,
    )
    message = format_hotspot_message(hotspots, config.SCHEDULE_TIMES)
    print(message)
    print(f"\n📏 Message length: {len(message)} chars")
    print()


if __name__ == "__main__":
    test_api_fetch()
    test_message_with_hotspots()
    test_message_no_hotspots()
    test_message_yesterday_only()
    test_real_data()
    print("=" * 60)
    print("✅ All tests completed!")
    print("=" * 60)
