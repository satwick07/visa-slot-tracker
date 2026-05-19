"""
Configuration for US Visa Slot Tracker
"""

# =============================================================================
# TELEGRAM BOT SETTINGS (for sending YOU notifications)
# =============================================================================
# Follow these steps to get your bot token and chat ID:
#
# 1. Open Telegram, search for @BotFather
# 2. Send /newbot, give it a name and username (must end in 'bot')
# 3. Copy the token BotFather gives you and paste below
#
# 4. Search for @userinfobot on Telegram
# 5. Start it - it will reply with your numeric ID
# 6. Copy that ID below
#
# 7. IMPORTANT: Search for your new bot on Telegram and tap "Start"
#    (otherwise it cannot send you messages)

# These are fallback values. On GitHub Actions, env vars override these.
# For local use, paste your values here. For GitHub, use repository secrets.
TELEGRAM_BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"  # or set env var TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID = "YOUR_CHAT_ID_HERE"      # or set env var TELEGRAM_CHAT_ID

# =============================================================================
# MONITORING SETTINGS
# =============================================================================

# How often to check (in seconds)
CHECK_INTERVAL_SECONDS = 300  # 5 minutes

# Visa type to watch for (case-insensitive match in messages)
VISA_TYPES_TO_WATCH = ["J1", "J-1", "Exchange Visitor", "J1/J2"]

# Cities/Consulates in India to watch for
INDIA_CITIES = ["Mumbai", "Delhi", "Chennai", "Hyderabad", "Kolkata", "India"]

# Country flags/names to watch for
INDIA_INDICATORS = ["India", "\U0001f1ee\U0001f1f3", "IN"]

# =============================================================================
# TELEGRAM CHANNELS TO MONITOR (public channels - no login needed)
# =============================================================================
# These are public Telegram channels that post visa slot updates.
# The script reads them via their public web preview (t.me/s/<channel>).
# Add more channels as you find them.

TELEGRAM_CHANNELS_TO_MONITOR = [
    "usvisa_slots",           # US Visa Slots F1-J1-B1/B2-K1 (multi-country, J1 included)
    "usvisaslots",            # US VISA SLOT STATUS
    # Add more public channels here as you discover them:
    # "channel_username",     # Description
]

# =============================================================================
# BROADENED MATCHING (to catch more alerts)
# =============================================================================
# Set this to True to also alert on ANY India visa slot post (not just J1).
# Useful to see what's available across all categories.
ALERT_ON_ANY_INDIA_SLOT = False

# =============================================================================
# ADDITIONAL PUBLIC SOURCES (web scraping)
# =============================================================================
# These URLs are checked for slot availability info.
# Add any public tracker URLs you find.

PUBLIC_TRACKER_URLS = [
    # Add URLs of public visa date tracker websites if you find any
]
