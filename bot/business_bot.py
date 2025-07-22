import asyncio
import logging
from typing import Dict, Type, Callable, Awaitable

from pyrogram import Client, filters, enums
from pyrogram.types import Message
from pyrogram.handlers import (
    MessageHandler,
    BusinessConnectionHandler,
    RawUpdateHandler,
    BusinessMessageHandler
)

from config.config import Config
from handlers import MediaHandlers, UpdateHandlers
from handlers.message_handlers import MessageHandlers
from handlers.command_handlers import CommandHandlers
from kafka import KafkaProducerService
from localization import LocalizationService
from mongodb import MongoDb
from mongodb.repositories import UserRepository, MessageRepository
from mongodb.servcies import MessageService

class BusinessBot:
    """
    Telegram Business Bot core class.
    Handles messages, media, updates, and integrates with MongoDB/Kafka.

    Responsibilities:
        - Register Pyrogram handlers (commands, media, business messages)
        - Manage bot lifecycle (start/stop)
        - Dependency injection for services/repositories
    """

    def __init__(
            self,
            config: Config,
            mongo_db: MongoDb,
            localization_service: LocalizationService,
            kafka_service: KafkaProducerService,
            user_repository: UserRepository,
            message_repository: MessageRepository,
            message_service: MessageService
    ) -> None:
        """
        Initialize bot with dependencies.

        Args:
            config: Bot configuration (API keys, etc.)
            mongo_db: MongoDB client instance
            localization_service: Handles i18n/l10n
            kafka_service: Kafka producer for event streaming
            user_repository: DB operations for users
            message_repository: DB operations for messages
            message_service: High-level message processing
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.client = Client(
            name=self.config.BOT_USERNAME,
            api_id=self.config.API_ID,
            api_hash=self.config.API_HASH,
            bot_token=self.config.BOT_TOKEN,
            parse_mode=enums.ParseMode.HTML,
        )
        self._shutdown_event = asyncio.Event()

        # Services & Repositories
        self.mongo_db = mongo_db
        self.localization_service = localization_service
        self.kafka_service = kafka_service
        self.user_repository = user_repository
        self.message_repository = message_repository
        self.message_service = message_service

        # Handlers
        self._init_handlers()

        # Message type to filter mapping
        self.message_filters: Dict[str, Type[filters.Filter]] = {
            "text": filters.text,
            "photo": filters.photo,
            "video": filters.video,
            "voice": filters.voice,
            "video_note": filters.video_note,
            "sticker": filters.sticker,
            "animation": filters.animation,
        }

        self._register_handlers()
        self.logger.info("Bot initialized")

    def _init_handlers(self) -> None:
        """Initialize all handler classes with injected dependencies."""
        self.command_handlers = CommandHandlers(
            self.localization_service,
            self.user_repository
        )
        self.media_handlers = MediaHandlers(
            self.localization_service,
            self.kafka_service,
            self.user_repository
        )
        self.update_handlers = UpdateHandlers(
            self.localization_service,
            self.kafka_service,
            self.user_repository,
            self.message_repository,
            self.message_service
        )
        self.message_handlers = MessageHandlers(
            self.kafka_service,
            self.localization_service,
            self.user_repository
        )

    def _register_handlers(self) -> None:
        """
        Register all Pyrogram event handlers.

        Includes:
            - Command handlers (/start)
            - Media handlers (contacts, etc.)
            - Business connection updates
            - Incoming/outgoing message handlers
            - Raw updates
        """
        # Command handlers
        self.client.add_handler(
            MessageHandler(
                self.command_handlers.handle_start_command,
                filters.command("start")
            )
        )

        # Media handlers
        self.client.add_handler(
            MessageHandler(
                self.media_handlers.handle_contact,
                filters.contact
            )
        )

        # Business connection handler
        self.client.add_handler(
            BusinessConnectionHandler(
                self.update_handlers.handle_connection_update
            )
        )

        # Register message type handlers
        for message_type, message_filter in self.message_filters.items():
            self._register_message_handlers(message_type, message_filter)

        # Raw updates handler
        self.client.add_handler(
            RawUpdateHandler(self.update_handlers.handle_raw_update)
        )

        self.logger.debug("All handlers registered")

    def _register_message_handlers(
            self,
            message_type: str,
            message_filter: Type[filters.Filter]
    ) -> None:
        """
        Register incoming/outgoing message handlers for a specific media type.

        Args:
            message_type: Message type identifier (e.g., "photo")
            message_filter: Pyrogram filter for the message type
        """
        # Incoming messages
        self.client.add_handler(
            BusinessMessageHandler(
                self._create_message_handler(
                    self.message_handlers.handle_incoming_message,
                    message_type
                ),
                message_filter & filters.incoming
            )
        )

        # Outgoing messages
        self.client.add_handler(
            BusinessMessageHandler(
                self._create_message_handler(
                    self.message_handlers.handle_outgoing_message,
                    message_type
                ),
                message_filter & filters.outgoing
            )
        )

    def _create_message_handler(
            self,
            handler_func: Callable[..., Awaitable[None]],
            message_type: str
    ) -> Callable[[Client, Message], Awaitable[None]]:
        """
        Factory for creating typed message handlers.

        Args:
            handler_func: Original handler function
            message_type: Message type to pass to handler

        Returns:
            Async handler function with pre-bound message_type
        """

        async def handler(client: Client, message: Message) -> None:
            await handler_func(client, message, message_type)

        return handler

    async def run(self) -> None:
        """Start the bot and block until shutdown."""
        await self.client.start()
        self.logger.info("Bot started successfully")
        await self._shutdown_event.wait()

    async def stop(self) -> None:
        """Gracefully shutdown the bot."""
        self.logger.info("Initiating shutdown...")
        await self._cleanup_resources()
        self._shutdown_event.set()
        self.logger.info("Bot stopped")

    async def _cleanup_resources(self) -> None:
        """Close all external connections."""
        try:
            self.mongo_db.close()
            await self.kafka_service.shutdown()
            await self.client.stop()
            self.logger.info("Resources cleaned up")
        except Exception as e:
            self.logger.info(f"Error during cleanup: {e}", exc_info=True)
            raise