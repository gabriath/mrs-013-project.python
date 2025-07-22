import logging

from pyrogram import Client
from pyrogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from typing import Optional, Dict, Any

from localization import LocalizationService
from mongodb.repositories import UserRepository


class CommandHandlers:
    """
    Handles Telegram bot commands with business logic for user interactions.

    Responsibilities:
        - Processing /start command with different user states
        - Managing business connection requirements
        - Handling premium user verification
        - Contact request flow initialization
    """

    def __init__(self, localization_service: LocalizationService, user_repository: UserRepository):
        """
        Initialize command handlers with required services.

        Args:
            localization_service: Service for localized text strings
            user_repository: Database access for user data
        """
        self.localization_service = localization_service
        self.user_repository = user_repository
        self.logger = logging.getLogger(__name__)

    async def handle_start_command(self, client: Client, message: Message) -> None:
        """
        Process /start command with different response scenarios:
        1. Existing bot users (connected/not connected)
        2. New premium users
        3. Non-premium users

        Args:
            client: Pyrogram Client instance
            message: Incoming message object

        Raises:
            Exception: Logs errors but doesn't interrupt flow
        """
        try:
            user: Optional[Dict[str, Any]] = self.user_repository.get_user_by_id(message.from_user.id)

            if user and user.get("is_bot_user"):
                await self._handle_existing_user(message, user)
            elif not user:
                await self._handle_new_user(message)

        except Exception as e:
            self.logger.info(f"Error processing message >>> \nError message: {e} \nMessage entity: \n{message}")

    async def _handle_existing_user(self, message: Message, user: Dict[str, Any]) -> None:
        """
        Handle response for existing bot users.

        Args:
            message: Original message object
            user: User data from database
        """
        if user.get("is_connected"):
            reply_text = self.localization_service.get_text("service_working", "ru")
        else:
            reply_text = self.localization_service.get_text("business_connection_required", "ru")

        await message.reply_text(text=reply_text)

    async def _handle_new_user(self, message: Message) -> None:
        """
        Handle response flow for new users.

        Args:
            message: Original message object
        """
        if not message.from_user.is_premium:
            reply_text = self.localization_service.get_text("premium_required", "ru")
            await message.reply_text(text=reply_text)
        else:
            await self._init_contact_request(message)

    async def _init_contact_request(self, message: Message) -> None:
        """
        Initialize contact sharing flow for premium users.

        Args:
            message: Original message object
        """
        request_contact_text = self.localization_service.get_text("request_contact", "ru")
        keyboard = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(request_contact_text, request_contact=True)]],
            one_time_keyboard=True,
            resize_keyboard=True
        )
        reply_text = self.localization_service.get_text("start", "ru")
        await message.reply_text(text=reply_text, reply_markup=keyboard)