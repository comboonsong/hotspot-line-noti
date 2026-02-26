#!/usr/bin/env python3
"""
LINE Hotspot Notification Bot
Fetches VIIRS hotspot data from GISTDA API and sends notifications to a LINE group.

Usage:
    python main.py           # Run with scheduler (06:00 and 14:00)
    python main.py --now     # Run once immediately (for testing)
"""

import argparse
import logging
import time

import schedule

from config import Config
from hotspot_api import fetch_hotspots
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
    """Fetch hotspots, format message, and send to LINE group."""
    logger.info("=== Starting hotspot notification job ===")

    try:
        # 1. Fetch hotspot data
        hotspots = fetch_hotspots(
            api_key=config.GISTDA_API_KEY,
            base_url=config.GISTDA_BASE_URL,
            province_idn=config.PROVINCE_IDN,
            limit=config.FETCH_LIMIT,
        )
        logger.info("Fetched %d hotspots.", len(hotspots))

        # 2. Format notification message
        message = format_hotspot_message(
            hotspots=hotspots,
            schedule_times=config.SCHEDULE_TIMES,
        )
        logger.info("Formatted message (%d chars).", len(message))

        # 3. Send to LINE group
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
    logger.info("Configuration loaded. Province IDN: %d", config.PROVINCE_IDN)
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
