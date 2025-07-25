import logging

from pyrogram import Client
from pyrogram.types import CallbackQuery, InputMediaVideo

from localization import LocalizationService


class CallbackHandlers:
    """
    Handles Telegram bot callbacks with business logic for user interactions.

    """

    def __init__(self, localization_service: LocalizationService):
        """
        Initialize callback handlers with required services.

        Args:
            localization_service: Service for localized text strings
        """
        self.localization_service = localization_service
        self.logger = logging.getLogger(__name__)

    async def handle_demonstration_callback(self, client: Client, callback_query: CallbackQuery):
        reply_text = self.localization_service.get_text("demonstration", "ru")
        videos = [
            InputMediaVideo(media="https://s3.twcstorage.ru/24581035-003b8477-2c98-4a4f-9119-8db193d1a3b6/IMG_0461.MP4", caption=reply_text),
            InputMediaVideo(media="https://s3.twcstorage.ru/24581035-003b8477-2c98-4a4f-9119-8db193d1a3b6/IMG_0464.MP4"),
            InputMediaVideo(media="https://s3.twcstorage.ru/24581035-003b8477-2c98-4a4f-9119-8db193d1a3b6/IMG_0465.MP4")
        ]
        await client.send_media_group(callback_query.from_user.id, videos)