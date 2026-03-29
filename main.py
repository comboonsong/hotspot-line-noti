#!/usr/bin/env python3
"""
LINE Hotspot Notification Bot
Fetches hotspot data from GISTDA directory API and sends notifications to a LINE group.

Usage:
    python main.py           # Run with scheduler
    python main.py --now     # Run once immediately
"""

import argparse
import logging
import os
import time
from datetime import datetime

import schedule

from config import Config
from gistda_excel import TZ_BANGKOK, download_and_parse_excel
from line_bot import send_group_message
from message_formatter import format_hotspot_message
from daily_logger import save_daily_messages

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def _write_github_output(key: str, value: str) -> None:
    """Write a key=value pair to $GITHUB_OUTPUT for GitHub Actions step outputs."""
    github_output = os.getenv("GITHUB_OUTPUT")
    if github_output and value:
        with open(github_output, "a") as f:
            f.write(f"{key}={value}\n")
        logger.info("GitHub output: %s=%s", key, value)


def job(config: Config) -> None:
    """Fetch hotspots from GISTDA, format & send to LINE, output state for GitHub Actions."""
    logger.info("=== Starting hotspot notification job ===")
    logger.info(
        "Window: start=%r end=%r",
        config.WINDOW_START or "(00:00)", config.WINDOW_END or "(now)",
    )

    try:
        now = datetime.now(TZ_BANGKOK)

        # 1. Download and parse GISTDA Excel files
        hotspots, files_downloaded, latest_hotspot_time = download_and_parse_excel(
            now=now,
            province_filter=config.PROVINCE_FILTER,
            window_start=config.WINDOW_START,
            window_end=config.WINDOW_END,
        )
        logger.info(
            "Parsed %d hotspots from %d files. Latest time: %s",
            len(hotspots), files_downloaded, latest_hotspot_time or "(none)",
        )

        # 2. Format notification message
        messages = format_hotspot_message(
            hotspots=hotspots,
            schedule_times=config.SCHEDULE_TIMES,
            now=now,
            window_start=config.WINDOW_START,
            window_end=config.WINDOW_END,
            mode=config.MESSAGE_MODE,
        )
        logger.info("Formatted %d message bubbles.", len(messages))

        # 3. Save full messages to daily JSON for the website
        save_daily_messages(
            messages=messages,
            window_start=config.WINDOW_START,
            window_end=config.WINDOW_END,
        )

        # 4. Prepare message to send to LINE group
        is_run_1 = (config.WINDOW_END == "0525" or not config.WINDOW_END)
        
        if is_run_1:
            messages_to_send = messages
            logger.info("Run 1 (Morning): Sending full message to LINE.")
        else:
            w_start = config.WINDOW_START
            w_end = config.WINDOW_END
            
            # Formulate human-readable time
            display_start = f"{w_start[:2]}:{w_start[2:]}น." if w_start and len(w_start) == 4 and w_start.isdigit() else w_start
            display_end = f"{w_end[:2]}:{w_end[2:]}น." if w_end and len(w_end) == 4 and w_end.isdigit() else w_end
            if not display_start:
                display_start = "00:00น." if now.hour < 12 else "12:00น."
            if not display_end:
                display_end = f"{now.strftime('%H:%M')}น."
                
            web_url = "https://comboonsong.github.io/hotspot-line-noti/"
            
            if hotspots:
                short_msg = f"🔥 พบจุดความร้อนเพิ่มเติม รอบเวลา {display_start} ถึง {display_end} โดยข้อความจะอยู่ใน {web_url}"
            else:
                short_msg = f"❌ ไม่พบจุดความร้อนเพิ่มเติม รอบเวลา {display_start} ถึง {display_end} โดยข้อความจะอยู่ใน {web_url}"
            
            messages_to_send = [short_msg]
            logger.info("Run 2+: Sending short summary message to LINE.")

        # 5. Send to LINE group
        send_group_message(
            channel_access_token=config.LINE_CHANNEL_ACCESS_TOKEN,
            group_id=config.LINE_GROUP_ID,
            message_texts=messages_to_send,
        )

        # 4. Output latest hotspot time for GitHub Actions state tracking
        #    (only output if hotspots were found — do not overwrite state on empty run)
        if latest_hotspot_time:
            _write_github_output("LATEST_HOTSPOT_TIME", latest_hotspot_time)

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

    config = Config()
    config.validate()
    logger.info("Province filter: %s | Mode: %s", config.PROVINCE_FILTER, config.MESSAGE_MODE)
    logger.info("Schedule times: %s", ", ".join(config.SCHEDULE_TIMES))

    if args.now:
        logger.info("Running job immediately (--now flag).")
        job(config)
        return

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
