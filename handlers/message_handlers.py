import logging

from pyrogram import Client
from pyrogram.types import Message, ReplyParameters
from typing import Optional, Dict, Any

from kafka.kafka_service import KafkaProducerService
from localization import LocalizationService
from mongodb.repositories import UserRepository


class MessageHandlers:
    """
    Handles incoming and outgoing Telegram messages with media processing capabilities.

    Responsibilities:
        - Processing incoming messages and forwarding to Kafka
        - Handling outgoing messages with media forwarding
        - Managing TTL media forwarding between users
        - Generating proper notifications for media messages
    """

    def __init__(
            self,
            kafka_service: KafkaProducerService,
            localization_service: LocalizationService,
            user_repository: UserRepository
    ) -> None:
        """
        Initialize message handlers with required services.

        Args:
            kafka_service: Service for sending messages to Kafka
            localization_service: Service for localized text strings
            user_repository: Database access for user data
        """
        self.kafka_service = kafka_service
        self.localization_service = localization_service
        self.user_repository = user_repository
        self.logger = logging.getLogger(__name__)

    async def handle_incoming_message(
            self,
            client: Client,
            message: Message,
            message_type: str
    ) -> None:
        """
        Process incoming messages by forwarding them to Kafka.

        Args:
            client: Pyrogram Client instance
            message: Incoming message object
            message_type: Type of message (text, photo, etc.)

        Note:
            Silently catches and logs errors to prevent message processing interruption.
        """
        try:
            await self.kafka_service.send_message(
                f"incoming_{message_type}_messages",
                message
            )
        except Exception as e:
            self.logger.info(f"Error processing message >>> \nError message: {e} \nMessage entity: \n{message}")

    async def handle_outgoing_message(
            self,
            client: Client,
            message: Message,
            message_type: str
    ) -> None:
        """
        Process outgoing messages with special handling for TTL media.

        Args:
            client: Pyrogram Client instance
            message: Outgoing message object
            message_type: Type of message (text, photo, etc.)

        Note:
            Handles special cases for media with TTL (Time-To-Live) and
            forwards them to the original sender with proper notifications.
        """
        try:
            user = self.user_repository.get_user_by_business_connection_id(
                message.business_connection_id
            )

            await self.kafka_service.send_message(
                f"outgoing_{message_type}_messages",
                message
            )

            if message.reply_to_message is not None:
                await self._process_ttl_media_reply(client, message, user)

        except Exception as e:
            self.logger.info(f"Error processing message >>> \nError message: {e} \nMessage entity: \n{message}")

    async def _process_ttl_media_reply(
            self,
            client: Client,
            message: Message,
            user: Dict[str, Any]
    ) -> None:
        """
        Handle TTL media in reply messages by forwarding to original sender.

        Args:
            client: Pyrogram Client instance
            message: Original outgoing message
            user: User data from database
        """
        reply = message.reply_to_message
        media_handlers = {
            'photo': ('photo', client.send_photo),
            'video': ('video', client.send_video),
            'voice': ('voice', client.send_voice),
            'video_note': ('video_note', client.send_video_note)
        }

        for media_type, (attr_name, sender) in media_handlers.items():
            media = getattr(reply, media_type, None)
            if self._should_forward_media(media, user, message):
                await self._forward_ttl_media(
                    client,
                    media_type,
                    media,
                    reply,
                    user,
                    sender
                )

    def _should_forward_media(
            self,
            media: Optional[Any],
            user: Dict[str, Any],
            message: Message
    ) -> bool:
        """
        Check if media should be forwarded based on TTL and user conditions.

        Args:
            media: Media object to check
            user: User data from database
            message: Original message object

        Returns:
            bool: True if media should be forwarded
        """
        return (media and hasattr(media, 'ttl_seconds')
                and media.ttl_seconds
                and user.get("_id") != message.from_user.id)

    async def _forward_ttl_media(
            self,
            client: Client,
            media_type: str,
            media: Any,
            reply: Message,
            user: Dict[str, Any],
            sender: callable
    ) -> None:
        """
        Forward TTL media to original sender with proper notification.

        Args:
            client: Pyrogram Client instance
            media_type: Type of media being forwarded
            media: Media object to forward
            reply: Reply message object
            user: User data from database
            sender: Appropriate Pyrogram sender function
        """
        file = await client.download_media(message=media, in_memory=True)
        displayed_name = get_user_displayed_name(
            reply.from_user.first_name,
            reply.from_user.last_name
        )

        text = self._prepare_media_notification_text(reply, displayed_name)

        if media_type == "video_note":
            sent_message = await client.send_video_note(
                chat_id=user.get("_id"),
                video_note=file
            )
            await client.send_message(
                chat_id=user.get("_id"),
                text=text,
                reply_parameters=ReplyParameters(
                    message_id=sent_message.id
                )
            )
        else:
            await sender(
                chat_id=user.get("_id"),
                caption=text,
                **{media_type: file}
            )

        # Update message attributes and forward to Kafka
        setattr(reply, media_type, file)
        setattr(reply, "business_connection_id", reply.business_connection_id)
        await self.kafka_service.send_message(
            f"incoming_{media_type}_messages",
            reply
        )

    def _prepare_media_notification_text(
            self,
            reply: Message,
            displayed_name: str
    ) -> str:
        """
        Prepare localized notification text for forwarded media.

        Args:
            reply: Original reply message
            displayed_name: Formatted user display name

        Returns:
            str: Localized notification text
        """
        base_params = {
            "key": "one_time_media_received",
            "lang": "ru",
            "user_id": reply.from_user.id,
            "name": displayed_name
        }

        if reply.caption:
            base_params["caption"] = self.localization_service.get_text(
                key="media_caption",
                caption=reply.caption
            )

        return self.localization_service.get_text(**base_params)


def get_user_displayed_name(
        first_name: Optional[str],
        last_name: Optional[str]
) -> Optional[str]:
    """
    Combine first and last names into a display string.

    Args:
        first_name: User's first name
        last_name: User's last name

    Returns:
        Optional[str]: Combined name if available, None otherwise
    """
    return " ".join(filter(None, [first_name, last_name])) or None