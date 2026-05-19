# US Visa Slot Tracker (J1 - India)

Automated tracker that monitors public Telegram channels for US J1 visa appointment slot availability in India and sends Telegram notifications when slots are detected.

## How It Works

1. Scrapes public Telegram channels (via `t.me/s/<channel>`) for visa slot posts
2. Filters for J1/Exchange Visitor visa mentions + India (Mumbai, Delhi, Chennai, Hyderabad, Kolkata)
3. Sends a Telegram notification when a matching slot is found
4. Runs automatically every 30 minutes via GitHub Actions

No login to ustraveldocs.com is required.

## Setup

### Prerequisites
- Python 3.10+
- A Telegram Bot (created via @BotFather)
- Your Telegram Chat ID (from @userinfobot)

### Local Usage

1. Clone this repo
2. Create a `.env` file:
   ```
   TELEGRAM_BOT_TOKEN=your_bot_token_here
   TELEGRAM_CHAT_ID=your_chat_id_here
   ```
3. Run:
   ```bash
   # Single check
   python tracker.py --once

   # Continuous monitoring (every 5 min)
   python tracker.py
   ```

### GitHub Actions (Automated)

The workflow runs every 30 minutes automatically. Secrets are configured in:
**Settings > Secrets and variables > Actions**

Required secrets:
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

To trigger manually: **Actions > Check US Visa Slots > Run workflow**

## Configuration

Edit `config.py` to customize:

| Setting | Description |
|---------|-------------|
| `CHECK_INTERVAL_SECONDS` | Poll interval for local continuous mode (default: 300s) |
| `VISA_TYPES_TO_WATCH` | Visa categories to match (default: J1, J-1, J1/J2) |
| `INDIA_CITIES` | Consulate cities to watch |
| `TELEGRAM_CHANNELS_TO_MONITOR` | Public Telegram channels to scrape |
| `ALERT_ON_ANY_INDIA_SLOT` | Set `True` to alert on any India slot, not just J1 |

## Files

| File | Purpose |
|------|---------|
| `tracker.py` | Main tracker logic |
| `config.py` | Configuration (channels, filters, intervals) |
| `send_test.py` | Send a manual test notification |
| `test_connection.py` | Verify bot and channel connectivity |
| `.env` | Local secrets (not committed) |
| `.github/workflows/check_slots.yml` | GitHub Actions schedule |

## Adding More Channels

Search Telegram for US visa slot channels and add their username to `TELEGRAM_CHANNELS_TO_MONITOR` in `config.py`:

```python
TELEGRAM_CHANNELS_TO_MONITOR = [
    "usvisa_slots",
    "usvisaslots",
    "new_channel_username",  # Add here
]
```

## Author

Satwick Nalli (satwicknalli@gmail.com)
