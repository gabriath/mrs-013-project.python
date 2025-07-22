from typing import Optional, Dict, Any

from mongodb import MongoDb

class MessageRepository:
    def __init__(self, db_connection: MongoDb, collection_name: str = 'messages'):
        self.collection = db_connection.db[collection_name]

    def get_message_by_id(self, message_id: str) -> Optional[Dict[str, Any]]:
        pipeline = [
            {"$match": {"_id": message_id}},
            {
                "$addFields": {
                    "converted_media_id": {"$toObjectId": "$media.$id"}
                }
            },
            {
                '$lookup': {
                    'from': 'users',
                    'localField': 'sender.$id',
                    'foreignField': '_id',
                    'as': 'sender'
                }
            },
            {'$unwind': {'path': '$sender', 'preserveNullAndEmptyArrays': True}},
            {
                '$lookup': {
                    'from': 'chats',
                    'localField': 'chat.$id',
                    'foreignField': '_id',
                    'as': 'chat'
                }
            },
            {'$unwind': {'path': '$chat', 'preserveNullAndEmptyArrays': True}},
            {
                '$lookup': {
                    'from': 'medias',
                    'localField': 'media.$id',
                    'foreignField': '_id',
                    'as': 'media'
                }
            },
            {'$unwind': {'path': '$media', 'preserveNullAndEmptyArrays': True}}
        ]

        result = list(self.collection.aggregate(pipeline))
        return result[0] if result else None

    def get_messages_by_ids(self, messages_ids: list[str]):
        pipeline = [
            {"$match": {"_id": {"$in": messages_ids}}},
            {
                "$addFields": {
                    "converted_media_id": {"$toObjectId": "$media.$id"}
                }
            },
            {
                "$lookup": {
                    "from": "medias",
                    "localField": "converted_media_id",
                    "foreignField": "_id",
                    "as": "media"
                }
            },
            {"$unwind": {"path": "$media", "preserveNullAndEmptyArrays": True}},
            {
                "$lookup": {
                    "from": "users",
                    "localField": "sender.$id",
                    "foreignField": "_id",
                    "as": "sender"
                }
            },
            {"$unwind": {"path": "$sender", "preserveNullAndEmptyArrays": True}},
            {
                "$lookup": {
                    "from": "chats",
                    "localField": "chat.$id",
                    "foreignField": "_id",
                    "as": "chat"
                }
            },
            {"$unwind": {"path": "$chat", "preserveNullAndEmptyArrays": True}}
        ]
        return list(self.collection.aggregate(pipeline))