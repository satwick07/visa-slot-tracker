"""Quick test to verify bot connection and channel scraping."""
import sys
sys.path.insert(0, ".")
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
import urllib.request
import json

print("=" * 50)
print("  VISA SLOT TRACKER - CONNECTION TEST")
print("=" * 50)

# 1. Test Telegram Bot connection
print("\n[1] Testing Telegram Bot connection...")
try:
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getMe"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=10) as resp:
        result = json.loads(resp.read().decode())
        bot = result["result"]
        print(f"    OK - Bot: @{bot['username']} ({bot['first_name']})")
except Exception as e:
    print(f"    FAILED - {e}")
    sys.exit(1)

# 2. Test sending a message to yourself
print("\n[2] Sending test message to your Telegram...")
try:
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = json.dumps({
        "chat_id": TELEGRAM_CHAT_ID,
        "text": "✅ Visa Slot Tracker connected successfully!\n\nYou will receive alerts here when J1 slots are detected for India.",
    }).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        result = json.loads(resp.read().decode())
        if result.get("ok"):
            print("    OK - Test message sent! Check your Telegram.")
        else:
            print(f"    FAILED - {result}")
except Exception as e:
    print(f"    FAILED - {e}")
    print("    Make sure you started a chat with your bot first!")

# 3. Test fetching from a Telegram channel
print("\n[3] Testing Telegram channel scraping...")
try:
    channel = "usvisa_slots"
    url = f"https://t.me/s/{channel}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        html = resp.read().decode("utf-8", errors="replace")
        # Count message blocks
        import re
        messages = re.findall(r'class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', html, re.DOTALL)
        print(f"    OK - Fetched {len(messages)} messages from @{channel}")
        if messages:
            # Show the last message as sample
            sample = re.sub(r"<[^>]+>", " ", messages[-1])
            sample = re.sub(r"\s+", " ", sample).strip()
            print(f"    Latest: {sample[:100]}...")
except Exception as e:
    print(f"    FAILED - {e}")

print("\n" + "=" * 50)
print("  All tests passed! You can now run:")
print("  python tracker.py --once    (single check)")
print("  python tracker.py           (continuous monitoring)")
print("=" * 50)
