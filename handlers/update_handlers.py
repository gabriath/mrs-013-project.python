import logging
from typing import Any, Dict, Optional

from pyrogram import Client
from pyrogram.raw.base import Update
from pyrogram.raw.types import UpdateBotDeleteBusinessMessage, UpdateBotEditBusinessMessage
from pyrogram.types import BusinessConnection, ReplyParameters

from kafka import KafkaProducerService
from localization import LocalizationService
from mongodb.repositories import UserRepository, MessageRepository
from mongodb.servcies import MessageService


class UpdateHandlers:
    """
    Handles various types of Telegram updates including:
    - Business connection status changes
    - Message deletions in business chats
    - Message edits in business chats

    Responsibilities:
        - Processing business connection events
        - Handling message deletion notifications
        - Managing message edit notifications
        - Maintaining proper message state in database
    """

    def __init__(
            self,
            localization_service: LocalizationService,
            kafka_service: KafkaProducerService,
            user_repository: UserRepository,
            message_repository: MessageRepository,
            message_service: MessageService
    ) -> None:
        """
        Initialize update handlers with required services.

        Args:
            localization_service: Service for localized text strings
            kafka_service: Kafka producer for event streaming
            user_repository: Database access for user data
            message_repository: Database access for message data
            message_service: High-level message operations
        """
        self.localization_service = localization_service
        self.kafka_service = kafka_service
        self.user_repository = user_repository
        self.message_repository = message_repository
        self.message_service = message_service
        self.logger = logging.getLogger(__name__)

    async def handle_connection_update(
            self,
            client: Client,
            connection: BusinessConnection
    ) -> None:
        """
        Handle business connection status updates.

        Args:
            client: Pyrogram Client instance
            connection: Business connection details

        Note:
            Sends appropriate notifications based on connection state changes.
        """
        try:
            user = self.user_repository.get_user_by_id(connection.user.id)
            self.user_repository.update_user_business_connection(
                connection.user.id,
                connection.id,
                connection.is_enabled
            )

            if not user:
                if connection.is_enabled:
                    reply_text = self.localization_service.get_text("start", "ru")
                    await client.send_message(connection.user.id, reply_text)
                return

            reply_text = self.localization_service.get_text(
                "business_connection_received" if connection.is_enabled
                else "business_connection_required",
                "ru"
            )
            await client.send_message(connection.user.id, reply_text)

        except Exception as e:
            self.logger.info(f"Error processing business connection >>> \nError message: {e} \nConnection entity: \n{connection}")

    async def handle_raw_update(
            self,
            client: Client,
            update: Update,
            users: Dict[str, Any],
            chats: Dict[str, Any]
    ) -> None:
        """
        Route raw updates to appropriate handlers.

        Args:
            client: Pyrogram Client instance
            update: Raw update object
            users: Dictionary of user information
            chats: Dictionary of chat information
        """
        if isinstance(update, UpdateBotDeleteBusinessMessage):
            await self.handle_deleted_message(client, update, users, chats)
        elif isinstance(update, UpdateBotEditBusinessMessage):
            await self.handle_edited_message(client, update, users, chats)

    async def handle_deleted_message(
            self,
            client: Client,
            update: UpdateBotDeleteBusinessMessage,
            users: Dict[str, Any],
            chats: Dict[str, Any]
    ) -> None:
        """
        Process deleted messages and notify relevant users.

        Args:
            client: Pyrogram Client instance
            update: Message deletion update
            users: Dictionary of user information
            chats: Dictionary of chat information
        """
        try:
            to_user = self.user_repository.get_user_by_business_connection_id(
                update.connection_id
            )
            if not to_user:
                return

            message_ids = self.message_service.generate_message_id(
                to_user.get("_id"),
                update.peer.user_id,
                update.messages
            )
            messages = self.message_repository.get_messages_by_ids(message_ids)

            for message in messages:
                await self._process_single_deleted_message(
                    client,
                    message,
                    to_user
                )

        except AttributeError:
            pass
        except Exception as e:
            self.logger.info(f"Error processing deleted message >>> \nError message: {e} \nUpdate entity: \n{update}")

    async def _process_single_deleted_message(
            self,
            client: Client,
            message: Dict[str, Any],
            to_user: Dict[str, Any]
    ) -> None:
        """
        Process notification for a single deleted message.

        Args:
            client: Pyrogram Client instance
            message: Deleted message data
            to_user: Recipient user data
        """
        if message.get("sender").get("_id") == to_user.get("_id"):
            return

        displayed_name = get_user_displayed_name(
            message.get("sender").get("first_name"),
            message.get("sender").get("last_name")
        )
        sender_id = message.get("sender").get("_id")
        message_type = message.get("type")
        content = message.get("caption") or message.get("text") or "null"

        handler_config = self._get_message_handler_config(message_type, content)
        if not handler_config:
            return

        text = self._prepare_deletion_notification(
            handler_config["text_key"],
            sender_id,
            displayed_name,
            content,
            message_type
        )

        await self._send_deletion_notification(
            client,
            handler_config,
            to_user.get("_id"),
            text
        )

    @staticmethod
    def _get_message_handler_config(
            message_type: str,
            content: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get configuration for handling specific message types.

        Args:
            message_type: Type of message being processed
            content: Message content/caption

        Returns:
            Optional configuration dictionary for the message type
        """
        handlers = {
            "TEXT_MESSAGE": {
                "method": "send_message",
                "text_key": "text_message_was_deleted",
                "args": {"text": content},
                "special_handler": None
            },
            "PHOTO_MESSAGE": {
                "method": "send_photo",
                "text_key": "media_message_was_deleted",
                "args": {"photo": "media.file_id", "caption": content},
                "special_handler": None
            },
            "VIDEO_MESSAGE": {
                "method": "send_video",
                "text_key": "media_message_was_deleted",
                "args": {"video": "media.file_id", "caption": content},
                "special_handler": None
            },
            "VOICE_MESSAGE": {
                "method": "send_voice",
                "text_key": "media_message_was_deleted",
                "args": {"voice": "media.file_id", "caption": content},
                "special_handler": None
            },
            "VIDEO_NOTE_MESSAGE": {
                "method": "send_video_note",
                "text_key": "video_note_was_deleted",
                "args": {"video_note": "media.file_id"},
                "special_handler": "_handle_video_note_deletion"
            },
            "STICKER_MESSAGE": {
                "method": "send_sticker",
                "text_key": "video_note_was_deleted",
                "args": {"sticker": "media.file_id"},
                "special_handler": "_handle_sticker_deletion"
            },
            "ANIMATION_MESSAGE": {
                "method": "send_animation",
                "text_key": "video_note_was_deleted",
                "args": {"animation": "media.file_id"},
                "special_handler": "_handle_animation_deletion"
            }
        }

        return handlers.get(message_type)

    def _prepare_deletion_notification(
            self,
            text_key: str,
            sender_id: int,
            displayed_name: str,
            content: str,
            message_type: str
    ) -> str:
        """
        Prepare localized notification text for deleted messages.

        Args:
            text_key: Localization key for the notification
            sender_id: ID of the message sender
            displayed_name: Formatted name of the sender
            content: Message content
            message_type: Type of the message

        Returns:
            Localized notification text
        """

        return self.localization_service.get_text(
            key=text_key,
            lang="ru",
            user_id=sender_id,
            name=displayed_name,
            **({"message": content} if message_type == "TEXT_MESSAGE" else {
                "caption": content} if content else {})
        )

    async def _send_deletion_notification(
            self,
            client: Client,
            handler_config: Dict[str, Any],
            chat_id: int,
            text: str
    ) -> None:
        """
        Send appropriate notification for deleted message.

        Args:
            client: Pyrogram Client instance
            handler_config: Handler configuration
            chat_id: ID of chat to send notification to
            text: Notification text
        """
        if handler_config["special_handler"]:
            special_handler = getattr(self, handler_config["special_handler"])
            await special_handler(client, chat_id, text, handler_config["args"])
        else:
            method = getattr(client, handler_config["method"])
            args = handler_config["args"].copy()
            if "caption" in args:
                args["caption"] = text
            else:
                args["text"] = text
            await method(chat_id, **args)

    @staticmethod
    async def _handle_video_note_deletion(
            client: Client,
            chat_id: int,
            text: str,
            args: Dict[str, Any]
    ) -> None:
        """Special handler for video note deletion notifications."""
        sent_message = await client.send_video_note(chat_id, **args)
        await client.send_message(
            chat_id=chat_id,
            text=text,
            reply_parameters=ReplyParameters(message_id=sent_message.id)
        )

    @staticmethod
    async def _handle_sticker_deletion(
            client: Client,
            chat_id: int,
            text: str,
            args: Dict[str, Any]
    ) -> None:
        """Special handler for sticker deletion notifications."""
        sent_message = await client.send_sticker(chat_id, **args)
        await client.send_message(
            chat_id=chat_id,
            text=text,
            reply_parameters=ReplyParameters(message_id=sent_message.id)
        )

    @staticmethod
    async def _handle_animation_deletion(
            client: Client,
            chat_id: int,
            text: str,
            args: Dict[str, Any]
    ) -> None:
        """Special handler for animation deletion notifications."""
        sent_message = await client.send_animation(chat_id, **args)
        await client.send_message(
            chat_id=chat_id,
            text=text,
            reply_parameters=ReplyParameters(message_id=sent_message.id)
        )

    async def handle_edited_message(
            self,
            client: Client,
            update: UpdateBotEditBusinessMessage,
            users: Dict[str, Any],
            chats: Dict[str, Any]
    ) -> None:
        """
        Process edited messages and notify relevant users.

        Args:
            client: Pyrogram Client instance
            update: Message edit update
            users: Dictionary of user information
            chats: Dictionary of chat information
        """
        try:
            to_user = self.user_repository.get_user_by_business_connection_id(update.connection_id)
            peer_user = self.user_repository.get_user_by_id(update.message.peer_id.user_id)

            if not to_user or not peer_user or to_user == peer_user:
                return

            message_id = self.message_service.generate_message_id(
                to_user.get("_id"),
                peer_user.get("_id"),
                update.message.id
            )
            message = self.message_repository.get_message_by_id(message_id)
            if message.get("type") != 'TEXT_MESSAGE':
                return

            displayed_name = get_user_displayed_name(
                peer_user.get("first_name"),
                peer_user.get("last_name")
            )

            text = self.localization_service.get_text(
                key="text_message_was_edited",
                lang="ru",
                user_id=peer_user.get("_id"),
                name=displayed_name,
                old_message=message.get("text"),
                new_message=update.message.message
            )

            await client.send_message(to_user.get("_id"), text)

        except Exception as e:
            self.logger.info(f"Error processing edited message >>> \nError message: {e} \nUpdate entity: \n{update}")


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
        Combined name if available, None otherwise
    """
    return " ".join(filter(None, [first_name, last_name])) or None