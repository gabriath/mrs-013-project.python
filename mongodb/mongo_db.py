import logging

from pymongo import MongoClient

from config.config import Config

class MongoDb:
    def __init__(self, config: Config):
        self.config = config
        self.host = self.config.MONGO_DB_HOST
        self.port = int(self.config.MONGO_DB_PORT)
        self.database_name = self.config.MONGO_DB_NAME
        self.client = MongoClient(self.host, self.port)
        self.db = self.client[self.database_name]
        self.logger = logging.getLogger(__name__)

    def close(self):
        self.logger.info("Mongo services shuting down...")
        self.client.close()
        self.logger.info("Mongo services stopped successfully")