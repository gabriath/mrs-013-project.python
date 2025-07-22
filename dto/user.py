from typing import Optional, List
from pyrogram import types


class UserDto:
    """
    Data Transfer Object (DTO) representing a Telegram user with business-specific fields.

    This class provides a structured way to store and access user information,
    including both basic Telegram user data and business connection details.

    Attributes:
        id (int): Unique identifier for the user.
        is_bot_user (Optional[bool]): Whether the user is a bot user.
        is_connected (Optional[bool]): Business connection status.
        business_connection_id (Optional[str]): ID of business connection.
        is_premium (Optional[bool]): Telegram Premium status.
        first_name (Optional[str]): User's first name.
        last_name (Optional[str]): User's last name.
        username (Optional[str]): Main username.
        usernames (Optional[List[types.Username]]): Additional usernames.
        language_code (Optional[str]): IETF language tag.
        dc_id (Optional[int]): Data center ID.
        phone_number (Optional[str]): Phone number in international format.
        photo (Optional[types.ChatPhoto]): Profile photo info.
    """

    def __init__(
            self,
            *,
            id: int,
            is_bot_user: Optional[bool],
            is_connected: Optional[bool],
            business_connection_id: Optional[str],
            is_premium: Optional[bool] = None,
            first_name: Optional[str] = None,
            last_name: Optional[str] = None,
            username: Optional[str] = None,
            usernames: Optional[List["types.Username"]] = None,
            language_code: Optional[str] = None,
            dc_id: Optional[int] = None,
            phone_number: Optional[str] = None,
            photo: Optional["types.ChatPhoto"] = None
    ) -> None:
        """
        Initialize UserDto with provided user information.

        Args:
            id: Unique user identifier (required).
            is_bot_user: True if user is a bot.
            is_connected: Business connection status.
            business_connection_id: Business connection ID.
            is_premium: Telegram Premium status.
            first_name: User's first name.
            last_name: User's last name.
            username: Primary username (@handle).
            usernames: List of additional usernames.
            language_code: User's language code (e.g., 'en').
            dc_id: Data center ID for user's account.
            phone_number: User's phone number.
            photo: ChatPhoto object with profile picture details.
        """
        # Required fields
        self.id = id
        self.is_bot_user = is_bot_user
        self.is_connected = is_connected
        self.business_connection_id = business_connection_id

        # Optional fields
        self.is_premium = is_premium
        self.first_name = first_name
        self.last_name = last_name
        self.username = username
        self.usernames = usernames
        self.language_code = language_code
        self.dc_id = dc_id
        self.phone_number = phone_number
        self.photo = photo

    @property
    def full_name(self) -> Optional[str]:
        """
        Get the user's full name by combining first and last names.

        Returns:
            Optional[str]: Combined first and last name if available,
                          None if neither name is set.

        Example:
            >>> user = UserDto(id=1, is_bot_user=False, is_connected=True,
            ...                business_connection_id="123", first_name="John",
            ...                last_name="Doe")
            >>> user.full_name
            'John Doe'
        """
        name_parts = filter(None, [self.first_name, self.last_name])
        return " ".join(name_parts) if any(name_parts) else None