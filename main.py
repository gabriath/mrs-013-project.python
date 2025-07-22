import asyncio
import signal
import logging
from typing import Optional

from config.config import Config
from config.logging import setup_logging
from kafka.kafka_service import KafkaProducerService
from bot.business_bot import BusinessBot
from localization import LocalizationService
from mongodb.mongo_db import MongoDb
from mongodb.repositories import UserRepository, MessageRepository
from mongodb.servcies import MessageService


async def main() -> None:
    """
    Main application entry point that initializes and runs the business bot.

    Responsibilities:
        - Initializes all service dependencies
        - Sets up signal handlers for graceful shutdown
        - Manages the application lifecycle
        - Handles cleanup on termination
    """
    # Initialize configuration and logging
    config = Config()
    setup_logging()
    # logging.getLogger("pyrogram").setLevel(logging.ERROR)
    logger = logging.getLogger(__name__)

    try:
        logger.info("Initializing application services...")

        # Database and storage services
        mongo_db = MongoDb(config)
        user_repository = UserRepository(mongo_db, "users")
        message_repository = MessageRepository(mongo_db, "messages")
        message_service = MessageService()

        # Localization and messaging
        localization_service = LocalizationService(config)
        kafka_service = KafkaProducerService(config)

        # Main bot instance
        bot = BusinessBot(
            config=config,
            mongo_db=mongo_db,
            localization_service=localization_service,
            kafka_service=kafka_service,
            user_repository=user_repository,
            message_repository=message_repository,
            message_service=message_service
        )

        # Set up graceful shutdown handlers
        loop = asyncio.get_running_loop()

        def handler(*_):
            return asyncio.create_task(bot.stop())

        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, handler, [])

        # Initialize and run services
        logger.info("Starting services...")
        await kafka_service.initialize()
        await bot.run()

    except Exception as e:
        logger.critical(f"Application failed: {e}", exc_info=True)
        raise
    finally:
        logger.info("Application shutdown complete")


async def graceful_shutdown(bot: Optional[BusinessBot] = None) -> None:
    """
    Handle graceful shutdown of the application.

    Args:
        bot: Optional BusinessBot instance to shut down
    """
    logger = logging.getLogger(__name__)
    logger.info("Initiating graceful shutdown...")

    if bot:
        await bot.stop()

    # Get all running tasks and cancel them
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    for task in tasks:
        task.cancel()

    logger.info("Cancelled pending tasks")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logging.critical(f"Unhandled exception: {e}", exc_info=True)
        raise