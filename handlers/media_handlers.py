import logging

from pyrogram import Client
from pyrogram.types import Message
from typing import Optional, Dict, Any

from dto import UserDto
from kafka.kafka_service import KafkaProducerService
from localization import LocalizationService
from mongodb.repositories import UserRepository


class MediaHandlers:
    """
    Handles media-related interactions in the Telegram bot, specifically contact sharing.

    Responsibilities:
        - Processing contact sharing from users
        - Validating user premium status
        - Creating user DTOs from contact messages
        - Sending user data to Kafka for processing
    """

    def __init__(
            self,
            localization_service: LocalizationService,
            kafka_service: KafkaProducerService,
            user_repository: UserRepository
    ) -> None:
        """
        Initialize media handlers with required services.

        Args:
            localization_service: Service for localized text strings
            kafka_service: Kafka producer for event streaming
            user_repository: Database access for user data
        """
        self.localization_service = localization_service
        self.kafka_service = kafka_service
        self.user_repository = user_repository
        self.logger = logging.getLogger(__name__)

    async def handle_contact(self, client: Client, message: Message) -> None:
        """
        Process incoming contact sharing with the following logic:
        1. Skip processing for existing bot users
        2. Reject non-premium users
        3. Create and process new user data for premium users

        Args:
            client: Pyrogram Client instance
            message: Incoming message containing contact

        Raises:
            Exception: Captures and logs processing errors
        """
        try:
            user: Optional[Dict[str, Any]] = self.user_repository.get_user_by_id(message.from_user.id)

            if user and user.get("is_bot_user"):
                return  # Skip processing for existing bot users

            if not user:
                await self._process_new_user_contact(message)

        except Exception as e:
            self.logger.info(f"Error processing message >>> \nError message: {e} \nMessage entity: \n{message}")

    async def _process_new_user_contact(self, message: Message) -> None:
        """
        Handle contact sharing from new users with premium check.

        Args:
            message: Message object containing contact info
        """
        if not message.from_user.is_premium:
            reply_text = self.localization_service.get_text("premium_required", "ru")
            await message.reply_text(text=reply_text)
        else:
            await self._create_and_process_user(message)

    async def _create_and_process_user(self, message: Message) -> None:
        """
        Create UserDto from contact message and send to Kafka.

        Args:
            message: Message object containing user contact
        """
        user_data = UserDto(
            id=message.from_user.id,
            is_bot_user=True,
            is_connected=False,
            business_connection_id=None,
            is_premium=message.from_user.is_premium,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
            username=message.from_user.username,
            usernames=message.from_user.usernames,
            language_code=message.from_user.language_code,
            dc_id=message.from_user.dc_id,
            phone_number=message.contact.phone_number,
            photo=message.from_user.photo
        )

        await self.kafka_service.send_message("users", user_data)

        reply_text = self.localization_service.get_text("phone_number_received", "ru")
        await message.reply_text(text=reply_text)