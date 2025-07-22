from typing import Union, List

from bson import ObjectId

class MessageService:
    def generate_message_id(self, first_user_id: int, second_user_id: int, message_id: Union[int, List[int]]) -> Union[str, List[str]]:
        """
        Generates an ObjectId from:
        - three individual arguments (first_user_id, second_user_id, message_id)
        - or two arguments (first_user_id, second_user_id) and list of ids (message_id)

        Returns a single ObjectId or a list of ObjectIds
        """
        if isinstance(message_id, int):
            return self.generate_single_message_id(first_user_id, second_user_id, message_id)
        else:
            return [self.generate_single_message_id(first_user_id, second_user_id, mid) for mid in message_id]

    def generate_single_message_id(self, first_user_id: int, second_user_id: int, message_id: int) -> str:
        """Helper function to generate a single ObjectId"""
        first_id = max(first_user_id, second_user_id)
        second_id = min(first_user_id, second_user_id)

        bytes_data = bytearray(12)

        bytes_data[0] = (message_id >> 24) & 0xff
        bytes_data[1] = (message_id >> 16) & 0xff
        bytes_data[2] = (message_id >> 8) & 0xff
        bytes_data[3] = message_id & 0xff

        bytes_data[4] = (first_id >> 24) & 0xff
        bytes_data[5] = (first_id >> 16) & 0xff
        bytes_data[6] = (first_id >> 8) & 0xff
        bytes_data[7] = first_id & 0xff

        bytes_data[8] = (second_id >> 24) & 0xff
        bytes_data[9] = (second_id >> 16) & 0xff
        bytes_data[10] = (second_id >> 8) & 0xff
        bytes_data[11] = second_id & 0xff

        return str(ObjectId(bytes(bytes_data)))