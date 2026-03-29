import json
import logging
import os
from datetime import datetime
from gistda_excel import TZ_BANGKOK
from message_formatter import _format_thai_date

logger = logging.getLogger(__name__)

DOCS_DIR = "docs"
DATA_FILE = os.path.join(DOCS_DIR, "daily_messages.json")

def _initialize_file(now: datetime) -> dict:
    return {
        "date": now.strftime("%Y-%m-%d"),
        "display_date": _format_thai_date(now),
        "rounds": []
    }

def save_daily_messages(messages: list[str], window_start: str, window_end: str) -> None:
    """Save the notification messages to the daily JSON file."""
    try:
        if not os.path.exists(DOCS_DIR):
            os.makedirs(DOCS_DIR)

        now = datetime.now(TZ_BANGKOK)
        current_date_str = now.strftime("%Y-%m-%d")

        data = None
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to read existing JSON, starting fresh: {e}")

        # Reset daily if the date doesn't match
        if not data or data.get("date") != current_date_str:
            data = _initialize_file(now)

        # Append new round
        display_start = f"{window_start[:2]}:{window_start[2:]}น." if window_start and len(window_start) == 4 and window_start.isdigit() else window_start
        display_end = f"{window_end[:2]}:{window_end[2:]}น." if window_end and len(window_end) == 4 and window_end.isdigit() else window_end
        
        if not display_start:
            display_start = "00:00น." if now.hour < 12 else "12:00น."
        if not display_end:
            display_end = f"{now.strftime('%H:%M')}น."

        round_name = f"รอบแจ้งเตือน {display_end}"

        new_round = {
            "time_window": round_name,
            "messages": messages
        }
        
        # Check if we already have this round (to prevent duplicates if ran manually twice)
        # We can just remove the old one or append
        existing_idx = -1
        for i, r in enumerate(data.get("rounds", [])):
            if r.get("time_window") == round_name:
                existing_idx = i
                break
                
        if existing_idx >= 0:
            data["rounds"][existing_idx] = new_round
        else:
            data["rounds"].append(new_round)

        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"Successfully saved {len(messages)} messages to {DATA_FILE} for {round_name}.")

    except Exception as e:
        logger.error(f"Failed to save messages to JSON: {e}", exc_info=True)
