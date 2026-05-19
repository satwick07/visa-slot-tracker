"""Send a manual test message via the Telegram bot."""
import os
import json
import urllib.request
from pathlib import Path

# Load .env
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())

token = os.environ.get("TELEGRAM_BOT_TOKEN")
chat_id = os.environ.get("TELEGRAM_CHAT_ID")

text = (
    "Visa Slot Tracker is alive and monitoring!\n\n"
    "This is a manual test. The bot is checking channels every 30 minutes.\n\n"
    "You will only be notified when a J1 slot for India is detected."
)

url = f"https://api.telegram.org/bot{token}/sendMessage"
payload = json.dumps({"chat_id": chat_id, "text": text}).encode("utf-8")
req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
resp = urllib.request.urlopen(req, timeout=10)
result = json.loads(resp.read().decode())
print("Message sent!" if result.get("ok") else f"Failed: {result}")
