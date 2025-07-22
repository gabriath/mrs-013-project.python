from typing import Optional, Dict, Any

from mongodb import MongoDb

class UserRepository:
    def __init__(self, db_connection: MongoDb, collection_name: str = 'users'):
        self.collection = db_connection.db[collection_name]

    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        return self.collection.find_one({'_id': user_id})

    def get_user_by_business_connection_id(self, business_connection_id: str):
        user = self.collection.find_one({'business_connection_id': business_connection_id})
        return user

    def update_user_business_connection(self, user_id: int, business_connection_id: str, is_connected: bool):
        self.collection.update_one(
            {'_id': user_id},
            {'$set': {'business_connection_id': business_connection_id, 'is_connected': is_connected}}
        )