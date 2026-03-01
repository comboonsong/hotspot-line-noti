#!/usr/bin/env python3
"""
LINE Hotspot Notification Bot
Fetches hotspot data via FIRMS API → GISTDA Excel and sends notifications to a LINE group.

Usage:
    python main.py           # Run with scheduler
    python main.py --now     # Run once immediately (for testing)
"""

import argparse
import logging
import time

import schedule

from config import Config
from firms_api import discover_pass_times
from gistda_excel import download_and_parse_excel
from line_bot import send_group_message
from message_formatter import format_hotspot_message

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def job(config: Config) -> None:
    """Fetch hotspots via FIRMS → GISTDA Excel, format message, and send to LINE group."""
    logger.info("=== Starting hotspot notification job ===")

    try:
        # 1. Discover satellite pass times from FIRMS
        pass_times = discover_pass_times(
            map_key=config.FIRMS_MAP_KEY,
            bbox=config.FIRMS_THA_BBOX,
            sources=config.FIRMS_SOURCES,
            firms_to_gistda=config.FIRMS_TO_GISTDA_SAT,
            sat_display=config.GISTDA_SAT_DISPLAY,
        )
        logger.info("Discovered %d pass times.", len(pass_times))

        # 2. Download and parse GISTDA Excel files
        hotspots, files_downloaded = download_and_parse_excel(
            pass_times=pass_times,
            province_filter=config.PROVINCE_FILTER,
        )
        logger.info("Parsed %d hotspots from %d Excel files.", len(hotspots), files_downloaded)

        # Detect when FIRMS found passes but GISTDA has no files yet
        gistda_unavailable = len(pass_times) > 0 and files_downloaded == 0

        # 3. Format notification message
        message = format_hotspot_message(
            hotspots=hotspots,
            schedule_times=config.SCHEDULE_TIMES,
            gistda_unavailable=gistda_unavailable,
        )
        logger.info("Formatted message (%d chars).", len(message))

        # 4. Send to LINE group
        send_group_message(
            channel_access_token=config.LINE_CHANNEL_ACCESS_TOKEN,
            group_id=config.LINE_GROUP_ID,
            message_text=message,
        )
        logger.info("=== Job completed successfully ===")

    except Exception as e:
        logger.error("=== Job failed: %s ===", e, exc_info=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="LINE Hotspot Notification Bot — VIIRS hotspot alerts for LINE groups."
    )
    parser.add_argument(
        "--now",
        action="store_true",
        help="Run the notification job once immediately and exit.",
    )
    args = parser.parse_args()

    # Load and validate config
    config = Config()
    config.validate()
    logger.info("Configuration loaded. Province filter: %s", config.PROVINCE_FILTER)
    logger.info("Schedule times: %s", ", ".join(config.SCHEDULE_TIMES))

    if args.now:
        logger.info("Running job immediately (--now flag).")
        job(config)
        return

    # Schedule jobs
    for t in config.SCHEDULE_TIMES:
        t = t.strip()
        schedule.every().day.at(t).do(job, config=config)
        logger.info("Scheduled job at %s every day.", t)

    logger.info("Scheduler started. Waiting for next job...")
    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()
