# Telegram Business Monitoring Bot

A sophisticated message tracking solution for Telegram business communications, providing real-time monitoring of message edits, deletions, and expiring content.

## Key Features

### Message Tracking Intelligence
- ✂️ **Deleted Message Detection** - Instant notifications when messages are removed
- ✏️ **Edit Tracking** - Full history of message edits with before/after comparison
- ⏳ **Ephemeral Media Capture** - Automatic preservation of view-once media (photos, videos)
- 📊 **Message Auditing** - Comprehensive logging of all message events

## Technical Architecture
Telegram Client (Pyrogram) → Kafka Event Stream → MongoDB Storage → Monitoring Interface

### Core Components
1. **Telegram Listener** (Pyrogram)
   - Real-time message monitoring
   - Business connection management
   - Real-time mesage edits monitoring

## Environment Configuration

Create `.env` file with these required variables:

```ini
# Telegram API
API_ID=[API ID] # Telegram API ID from my.telegram.org
API_HASH=[API HASH] # Telegram API Hash from my.telegram.org
BOT_TOKEN=[YOUR BOT TOKEN] # Bot token from @BotFather
BOT_USERNAME=[BOT USERNAME] # Bot username without @

# Kafka
KAFKA_BOOTSTRAP_SERVERS=host # Kafka broker addresses

# MongoDB
MONGO_DB_HOST=host # MongoDB host
MONGO_DB_PORT=port # MongoDB port
MONGO_DB_NAME=db_name # Database name

# Features
ADMIN_ID=bot_admin_id # Your Telegram user ID for admin access
LOCALES_DIRECTORY_PATH=localization/locales # Path to locale files
```

