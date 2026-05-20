"""
Interactive Telegram Bot Listener for Visa Slot Tracker.

Run this script to make the bot respond to your messages.
When you message the bot, it will:
  - Run an immediate slot check
  - Reply with results and status

Usage:
  python bot_listener.py

Keep it running in a terminal window. Press Ctrl+C to stop.
"""

import os
import re
import json
import time
import logging
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

# Load .env
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())

from config import (
    VISA_TYPES_TO_WATCH,
    INDIA_CITIES,
    INDIA_INDICATORS,
    TELEGRAM_CHANNELS_TO_MONITOR,
)

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def telegram_api(method: str, params: dict = None) -> dict:
    """Call Telegram Bot API."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/{method}"
    if params:
        payload = json.dumps(params).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    else:
        req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def send_reply(chat_id: str, text: str):
    """Send a reply message."""
    telegram_api("sendMessage", {"chat_id": chat_id, "text": text})


def fetch_channel_messages(channel_name: str) -> list[str]:
    """Fetch recent messages from a public Telegram channel."""
    url = f"https://t.me/s/{channel_name}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as response:
            html = response.read().decode("utf-8", errors="replace")
    except Exception as e:
        return [f"[Error fetching @{channel_name}: {e}]"]

    messages = []
    pattern = r'class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>'
    matches = re.findall(pattern, html, re.DOTALL)
    for match in matches:
        clean_text = re.sub(r"<[^>]+>", " ", match)
        clean_text = re.sub(r"\s+", " ", clean_text).strip()
        if clean_text:
            messages.append(clean_text)
    return messages


def is_relevant(message: str) -> bool:
    """Check if message is about J1 visa in India."""
    msg_upper = message.upper()
    has_visa = any(v.upper() in msg_upper for v in VISA_TYPES_TO_WATCH)
    has_exchange = "EXCHANGE" in msg_upper or "J-1" in msg_upper or "J1" in msg_upper
    has_india = any(i.upper() in msg_upper for i in INDIA_INDICATORS)
    has_city = any(c.upper() in msg_upper for c in INDIA_CITIES)
    return (has_visa or has_exchange) and (has_india or has_city)


def run_check_and_report() -> str:
    """Run a full check and return a human-readable report."""
    results = []
    total_messages = 0
    matches = []

    for channel in TELEGRAM_CHANNELS_TO_MONITOR:
        messages = fetch_channel_messages(channel)
        total_messages += len(messages)

        for msg in messages:
            if is_relevant(msg):
                matches.append(f"  [@{channel}]: {msg[:150]}")

    report_lines = [
        "--- Visa Slot Check Report ---",
        f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Channels checked: {len(TELEGRAM_CHANNELS_TO_MONITOR)}",
        f"  {', '.join('@' + c for c in TELEGRAM_CHANNELS_TO_MONITOR)}",
        f"Total messages scanned: {total_messages}",
        f"Watching for: {', '.join(VISA_TYPES_TO_WATCH)}",
        f"Cities: {', '.join(INDIA_CITIES)}",
        "",
    ]

    if matches:
        report_lines.append(f"FOUND {len(matches)} matching slot(s):")
        report_lines.extend(matches)
    else:
        report_lines.append("No J1 India slots found right now.")
        report_lines.append("")
        report_lines.append("The bot checks automatically every 30 min via GitHub Actions.")
        report_lines.append("You'll get an alert the moment a slot appears.")

    return "\n".join(report_lines)


def handle_message(message: dict):
    """Handle an incoming message from the user."""
    chat_id = message["chat"]["id"]
    text = message.get("text", "").strip().lower()

    # Any message triggers a check
    if text in ("/start", "start"):
        reply = (
            "Visa Slot Tracker Bot - Active!\n\n"
            "Commands:\n"
            "  /check - Run an immediate slot check\n"
            "  /status - Show bot status\n"
            "  Any other message - Also runs a check\n\n"
            "The bot also runs automatically every 30 min via GitHub Actions.\n"
            "When a J1 India slot is detected, you'll get a notification here."
        )
    elif text in ("/status", "status"):
        reply = (
            f"Bot Status: ACTIVE\n"
            f"Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Monitoring channels: {', '.join('@' + c for c in TELEGRAM_CHANNELS_TO_MONITOR)}\n"
            f"Watching for: {', '.join(VISA_TYPES_TO_WATCH)}\n"
            f"Cities: {', '.join(INDIA_CITIES)}\n"
            f"GitHub Actions: Running every 30 min\n"
            f"Bot listener: Running on your PC"
        )
    else:
        # Any other message (including /check, images, etc.) → run check
        send_reply(chat_id, "Checking slots now...")
        reply = run_check_and_report()

    send_reply(chat_id, reply)


def poll_updates():
    """Long-poll for new messages from Telegram."""
    logger.info("=" * 50)
    logger.info("  Visa Slot Tracker Bot - LISTENING")
    logger.info("  Send any message to @us_satwick_visa_bot")
    logger.info("  to trigger an immediate slot check.")
    logger.info("  Press Ctrl+C to stop.")
    logger.info("=" * 50)

    offset = 0

    while True:
        try:
            params = {"offset": offset, "timeout": 30}
            result = telegram_api("getUpdates", params)

            if result.get("ok") and result.get("result"):
                for update in result["result"]:
                    offset = update["update_id"] + 1

                    if "message" in update:
                        msg = update["message"]
                        sender = msg.get("from", {}).get("first_name", "Unknown")
                        text = msg.get("text", "[non-text message]")
                        logger.info(f"Message from {sender}: {text}")
                        handle_message(msg)

        except KeyboardInterrupt:
            logger.info("Bot stopped by user.")
            break
        except Exception as e:
            logger.error(f"Error: {e}")
            time.sleep(5)


if __name__ == "__main__":
    poll_updates()
