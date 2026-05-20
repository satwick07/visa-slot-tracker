"""
Bot Responder - Runs via GitHub Actions every 5 minutes.
Checks for any unread messages sent to the bot, replies with slot check results, then exits.
"""

import os
import re
import json
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

# Load .env for local testing
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

# File to track last processed update_id
OFFSET_FILE = Path(__file__).parent / "last_update_offset.txt"


def telegram_api(method: str, params: dict = None) -> dict:
    """Call Telegram Bot API."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/{method}"
    if params:
        payload = json.dumps(params).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    else:
        req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


def send_reply(chat_id, text: str):
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
        f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC",
        f"Channels checked: {len(TELEGRAM_CHANNELS_TO_MONITOR)}",
        f"  {', '.join('@' + c for c in TELEGRAM_CHANNELS_TO_MONITOR)}",
        f"Total messages scanned: {total_messages}",
        f"Watching for: {', '.join(VISA_TYPES_TO_WATCH)}",
        f"Cities: {', '.join(INDIA_CITIES)}",
        "",
    ]

    if matches:
        report_lines.append(f"FOUND {len(matches)} matching slot(s)!")
        report_lines.extend(matches)
    else:
        report_lines.append("No J1 India slots found right now.")
        report_lines.append("")
        report_lines.append("I check automatically every 5 min.")
        report_lines.append("You'll get an alert the moment a slot appears.")

    return "\n".join(report_lines)


def get_offset() -> int:
    """Get last processed update offset."""
    if OFFSET_FILE.exists():
        try:
            return int(OFFSET_FILE.read_text().strip())
        except (ValueError, IOError):
            return 0
    return 0


def save_offset(offset: int):
    """Save last processed update offset."""
    OFFSET_FILE.write_text(str(offset))


def handle_message(message: dict):
    """Handle an incoming message."""
    chat_id = message["chat"]["id"]
    text = message.get("text", "").strip().lower()

    if text in ("/start", "start"):
        reply = (
            "Visa Slot Tracker Bot - Active!\n\n"
            "Commands:\n"
            "  /check - Run an immediate slot check\n"
            "  /status - Show bot status\n"
            "  Any message - Also triggers a check\n\n"
            "I run on GitHub Actions every 5 min.\n"
            "I also check for J1 India slots every 30 min automatically.\n"
            "You'll get a notification when a slot is found."
        )
    elif text in ("/status", "status"):
        reply = (
            f"Bot Status: ACTIVE (GitHub Actions)\n"
            f"Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
            f"Channels: {', '.join('@' + c for c in TELEGRAM_CHANNELS_TO_MONITOR)}\n"
            f"Watching: {', '.join(VISA_TYPES_TO_WATCH)}\n"
            f"Cities: {', '.join(INDIA_CITIES)}\n"
            f"Slot check: Every 30 min\n"
            f"Message check: Every 5 min"
        )
    else:
        # Any other message → run check
        send_reply(chat_id, "Checking slots now...")
        reply = run_check_and_report()

    send_reply(chat_id, reply)


def main():
    """Check for unread messages, reply, exit."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Checking for new messages...")

    offset = get_offset()
    params = {"offset": offset, "timeout": 5}

    try:
        result = telegram_api("getUpdates", params)
    except Exception as e:
        print(f"Error fetching updates: {e}")
        return

    if not result.get("ok"):
        print(f"API error: {result}")
        return

    updates = result.get("result", [])

    if not updates:
        print("No new messages.")
        return

    print(f"Found {len(updates)} new message(s). Processing...")

    for update in updates:
        offset = update["update_id"] + 1

        if "message" in update:
            msg = update["message"]
            sender = msg.get("from", {}).get("first_name", "Unknown")
            text = msg.get("text", "[non-text]")
            print(f"  From {sender}: {text}")
            handle_message(msg)

    save_offset(offset)
    print("Done. All messages replied to.")


if __name__ == "__main__":
    main()
