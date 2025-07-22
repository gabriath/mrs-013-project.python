import os
from pathlib import Path
from typing import Dict, Type

from dotenv import load_dotenv
from pyrogram import filters

env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(env_path)


class BotConfig:
    """Bot-specific configuration including message filters."""

    # Message types and their corresponding Pyrogram filters
    MESSAGE_FILTERS: Dict[str, Type[filters.Filter]] = {
        "text": filters.text,
        "photo": filters.photo,
        "video": filters.video,
        "voice": filters.voice,
        "video_note": filters.video_note,
        "sticker": filters.sticker,
        "animation": filters.animation,
    }

class Config:
    """Main configuration class."""

    def __init__(self):
        self.ADMIN_ID = os.getenv('ADMIN_ID')

        self.BOT_USERNAME = os.getenv('BOT_USERNAME')
        self.API_ID = os.getenv('API_ID')
        self.API_HASH = os.getenv('API_HASH')
        self.BOT_TOKEN = os.getenv('BOT_TOKEN')

        self.KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
        self.MONGO_DB_HOST = os.getenv('MONGO_DB_HOST', 'localhost')
        self.MONGO_DB_PORT = os.getenv('MONGO_DB_PORT', 27017)
        self.MONGO_DB_NAME = os.getenv('MONGO_DB_NAME', 'mrs_013_project')

        self.LOCALES_DIRECTORY_PATH = os.getenv('LOCALES_DIRECTORY_PATH', 'locales')

        self.message_filters = BotConfig.MESSAGE_FILTERS