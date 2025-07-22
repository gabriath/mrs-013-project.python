import base64
import logging
from datetime import datetime
from typing import Any, Dict, Optional, Union

from pyrogram.types import User, Chat, Photo, Video, Audio, Document, Voice, Sticker, Location, Contact
from aiokafka import AIOKafkaProducer
import json

from config.config import Config


class KafkaProducerService:
    """
    A service for producing messages to Kafka topics with Pyrogram object serialization.

    Handles:
    - Connection management to Kafka cluster
    - Serialization of Pyrogram objects
    - Reliable message delivery with error handling
    """

    def __init__(self, config: Config) -> None:
        """
        Initialize the Kafka producer service.

        Args:
            config: Application configuration containing Kafka settings
        """
        self.producer: Optional[AIOKafkaProducer] = None
        self.config = config
        self.logger = logging.getLogger(__name__)

    async def initialize(self) -> None:
        """
        Initialize the Kafka producer connection.

        Should be called before sending any messages.
        """
        try:
            self.producer = AIOKafkaProducer(
                bootstrap_servers=self.config.KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                retry_backoff_ms=500,  # Exponential backoff for retries
                max_batch_size=16384,  # 16KB batch size
                linger_ms=5,  # Wait up to 5ms for batching
            )
            await self.producer.start()
            self.logger.info("Kafka producer initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize Kafka producer: {e}")
            raise

    async def shutdown(self) -> None:
        """
        Gracefully shutdown the Kafka producer.

        Should be called when the service is no longer needed.
        """
        try:
            self.logger.info("Shutting down Kafka producer...")
            if self.producer:
                await self.producer.stop()
            self.logger.info("Kafka producer stopped successfully")
        except Exception as e:
            self.logger.error(f"Error during Kafka producer shutdown: {e}")
            raise

    def message_to_dict(self, data: Any) -> Dict[str, Any]:
        """
        Recursively convert Pyrogram objects to serializable dictionaries.

        Args:
            data: The input data to convert (Pyrogram object or primitive)

        Returns:
            Dictionary representation of the input data

        Note:
            - Skips private attributes and callable methods
            - Handles nested Pyrogram objects
            - Converts special types (datetime, bytes) to strings
        """
        if data is None:
            return None

        # Handle primitive types directly
        if isinstance(data, (str, int, float, bool)):
            return data

        result = {}
        ignored_attrs = {"_client", "_raw"}  # Internal Pyrogram attributes to skip

        for attr in dir(data):
            # Skip private attributes and special cases
            if attr.startswith("_") or attr in ignored_attrs:
                continue

            try:
                value = getattr(data, attr)

                # Skip callable methods
                if callable(value):
                    continue

                # Recursively handle nested objects
                if isinstance(value, (User, Chat, Photo, Video, Audio,
                                      Document, Voice, Sticker, Location, Contact)):
                    value = self.message_to_dict(value)
                elif isinstance(value, list):
                    value = [
                        self.message_to_dict(item)
                        if hasattr(item, "__dict__")
                        else item
                        for item in value
                    ]
                elif hasattr(value, "__dict__"):
                    value = self.message_to_dict(value)
                elif isinstance(value, datetime):
                    value = value.isoformat()  # Convert datetime to ISO string
                elif isinstance(value, bytes):
                    value = base64.b64encode(value).decode("utf-8")  # Bytes to base64
                elif isinstance(value, set):
                    value = list(value)  # Convert sets to lists

                result[attr] = value

            except Exception as e:
                self.logger.warning(f"Could not serialize attribute {attr}: {e}")
                continue

        return result

    async def send_message(
            self,
            topic: str,
            data: Union[Any, Dict[str, Any]]
    ) -> bool:
        """
        Send a message to a Kafka topic.

        Args:
            topic: The Kafka topic to send to
            data: The message data (Pyrogram object or dict)

        Returns:
            bool: True if message was sent successfully, False otherwise

        Note:
            Automatically serializes Pyrogram objects before sending
        """
        if not self.producer:
            self.logger.error("Kafka producer not initialized")
            return False

        try:
            serialized = self.message_to_dict(data)
            await self.producer.send_and_wait(topic, value=serialized)
            self.logger.debug(f"Message sent to topic {topic}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to send message to {topic}: {e}")
            return False