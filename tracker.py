"""
US Visa Slot Tracker for J1 Visa - India
Monitors public Telegram channels and sends you alerts when J1 slots appear.

No login to ustraveldocs.com required.
"""

import os
import re
import time
import json
import hashlib
import logging
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path
from html.parser import HTMLParser


def _load_dotenv():
    """Load .env file if it exists (for local development)."""
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())


_load_dotenv()

from config import (
    TELEGRAM_BOT_TOKEN as _CONFIG_BOT_TOKEN,
    TELEGRAM_CHAT_ID as _CONFIG_CHAT_ID,
    CHECK_INTERVAL_SECONDS,
    VISA_TYPES_TO_WATCH,
    INDIA_CITIES,
    INDIA_INDICATORS,
    TELEGRAM_CHANNELS_TO_MONITOR,
)

# Environment variables override config file (for GitHub Actions / CI)
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", _CONFIG_BOT_TOKEN)
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", _CONFIG_CHAT_ID)

# Optional config
try:
    from config import ALERT_ON_ANY_INDIA_SLOT
except ImportError:
    ALERT_ON_ANY_INDIA_SLOT = False

# =============================================================================
# LOGGING SETUP
# =============================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# File to track already-sent alerts (avoid duplicates)
SEEN_FILE = Path(__file__).parent / "seen_messages.json"


# =============================================================================
# HTML PARSER - Extract messages from Telegram public channel pages
# =============================================================================
class TelegramMessageParser(HTMLParser):
    """Parse messages from t.me/s/<channel> HTML pages."""

    def __init__(self):
        super().__init__()
        self.messages = []
        self._in_message = False
        self._current_text = ""
        self._capture = False

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        class_name = attrs_dict.get("class", "")
        # Telegram uses 'tgme_widget_message_text' for message content
        if "tgme_widget_message_text" in class_name:
            self._in_message = True
            self._current_text = ""
            self._capture = True

    def handle_endtag(self, tag):
        if self._in_message and tag in ("div", "span"):
            # Try to close on the right tag
            if self._current_text.strip():
                self.messages.append(self._current_text.strip())
            self._in_message = False
            self._capture = False
            self._current_text = ""

    def handle_data(self, data):
        if self._capture:
            self._current_text += data + " "


def fetch_telegram_channel_messages(channel_name: str) -> list[str]:
    """
    Fetch recent messages from a public Telegram channel.
    Uses the public web preview at t.me/s/<channel>.
    """
    url = f"https://t.me/s/{channel_name}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as response:
            html = response.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, urllib.error.HTTPError) as e:
        logger.warning(f"Failed to fetch channel @{channel_name}: {e}")
        return []

    # Extract message text blocks using regex (more reliable than parser for Telegram)
    messages = []

    # Pattern 1: tgme_widget_message_text contains the message body
    pattern = r'class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>'
    matches = re.findall(pattern, html, re.DOTALL)

    for match in matches:
        # Strip HTML tags from the message content
        clean_text = re.sub(r"<[^>]+>", " ", match)
        clean_text = re.sub(r"\s+", " ", clean_text).strip()
        if clean_text:
            messages.append(clean_text)

    # Fallback: try simpler extraction if regex didn't work
    if not messages:
        # Try extracting any text between message divs
        simple_pattern = r'data-post="[^"]*"[^>]*>.*?<div[^>]*>(.*?)</div>'
        simple_matches = re.findall(simple_pattern, html, re.DOTALL)
        for match in simple_matches:
            clean_text = re.sub(r"<[^>]+>", " ", match)
            clean_text = re.sub(r"\s+", " ", clean_text).strip()
            if len(clean_text) > 10:
                messages.append(clean_text)

    logger.info(f"Fetched {len(messages)} messages from @{channel_name}")
    return messages


def is_relevant_message(message: str) -> bool:
    """
    Check if a message is relevant to J1 visa slots in India.
    Returns True if the message mentions both a J1 visa type AND India.
    If ALERT_ON_ANY_INDIA_SLOT is True, alerts on any India slot regardless of type.
    """
    msg_upper = message.upper()

    # Check if message mentions India or Indian cities
    has_india = any(indicator.upper() in msg_upper for indicator in INDIA_INDICATORS)
    has_city = any(city.upper() in msg_upper for city in INDIA_CITIES)
    is_india_related = has_india or has_city

    # If broadened matching is on, any India slot triggers alert
    if ALERT_ON_ANY_INDIA_SLOT and is_india_related:
        return True

    # Check if message mentions any watched visa type
    has_visa_type = any(vtype.upper() in msg_upper for vtype in VISA_TYPES_TO_WATCH)

    # For J1, also match generic "Exchange" or "Visitor"
    has_exchange = "EXCHANGE" in msg_upper or "J-1" in msg_upper or "J1" in msg_upper

    return (has_visa_type or has_exchange) and is_india_related


def get_message_hash(message: str) -> str:
    """Generate a hash for deduplication."""
    return hashlib.md5(message.encode()).hexdigest()


def load_seen_messages() -> set:
    """Load previously seen message hashes."""
    if SEEN_FILE.exists():
        try:
            data = json.loads(SEEN_FILE.read_text())
            return set(data)
        except (json.JSONDecodeError, IOError):
            return set()
    return set()


def save_seen_messages(seen: set):
    """Save seen message hashes. Keep only last 1000 to prevent file bloat."""
    recent = list(seen)[-1000:]
    SEEN_FILE.write_text(json.dumps(recent))


def send_telegram_notification(message: str, source_channel: str):
    """Send a Telegram message to yourself via your bot."""
    if TELEGRAM_BOT_TOKEN == "YOUR_BOT_TOKEN_HERE" or TELEGRAM_CHAT_ID == "YOUR_CHAT_ID_HERE":
        logger.warning("Telegram bot not configured! Printing alert to console only.")
        print(f"\n{'='*60}")
        print(f"  ALERT: J1 VISA SLOT DETECTED!")
        print(f"  Source: @{source_channel}")
        print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  Message: {message}")
        print(f"{'='*60}\n")
        return

    text = (
        f"J1 Visa Slot Alert!\n\n"
        f"Source: @{source_channel}\n"
        f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        f"{message}"
    )

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = json.dumps({
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
    }).encode("utf-8")

    headers = {"Content-Type": "application/json"}

    try:
        req = urllib.request.Request(url, data=payload, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as response:
            result = json.loads(response.read().decode())
            if result.get("ok"):
                logger.info("Telegram notification sent successfully!")
            else:
                logger.error(f"Telegram API error: {result}")
    except Exception as e:
        logger.error(f"Failed to send Telegram notification: {e}")
        # Still print to console as fallback
        print(f"\n[ALERT] J1 slot from @{source_channel}: {message}\n")


def check_all_channels():
    """Check all configured channels for relevant messages."""
    seen = load_seen_messages()
    new_alerts = 0

    for channel in TELEGRAM_CHANNELS_TO_MONITOR:
        logger.info(f"Checking channel: @{channel}")
        messages = fetch_telegram_channel_messages(channel)

        for msg in messages:
            msg_hash = get_message_hash(msg)

            # Skip already-seen messages
            if msg_hash in seen:
                continue

            # Mark as seen regardless of relevance (to avoid re-checking)
            seen.add(msg_hash)

            # Check if relevant to J1 India
            if is_relevant_message(msg):
                logger.info(f"MATCH FOUND in @{channel}: {msg[:80]}...")
                send_telegram_notification(msg, channel)
                new_alerts += 1

        # Small delay between channels to be polite
        time.sleep(2)

    save_seen_messages(seen)
    return new_alerts


def run_once():
    """Run a single check cycle (useful for testing)."""
    logger.info("Running single check...")
    alerts = check_all_channels()
    logger.info(f"Check complete. Found {alerts} new relevant alert(s).")
    return alerts


def run_continuous():
    """Run continuously, checking at configured intervals."""
    logger.info("=" * 60)
    logger.info("  US Visa J1 Slot Tracker - Starting")
    logger.info(f"  Monitoring channels: {TELEGRAM_CHANNELS_TO_MONITOR}")
    logger.info(f"  Watching for: {VISA_TYPES_TO_WATCH}")
    logger.info(f"  Cities: {INDIA_CITIES}")
    logger.info(f"  Check interval: {CHECK_INTERVAL_SECONDS}s")
    logger.info("=" * 60)

    if TELEGRAM_BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        logger.warning(
            "Telegram bot not configured. Alerts will print to console only.\n"
            "Edit config.py to add your bot token and chat ID for push notifications."
        )

    while True:
        try:
            check_all_channels()
        except Exception as e:
            logger.error(f"Error during check cycle: {e}")

        logger.info(f"Next check in {CHECK_INTERVAL_SECONDS} seconds...")
        time.sleep(CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
    import sys

    if "--once" in sys.argv:
        run_once()
    else:
        run_continuous()
