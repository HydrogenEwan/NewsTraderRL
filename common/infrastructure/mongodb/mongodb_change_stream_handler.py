from abc import ABC
from pymongo import MongoClient
from pymongo.errors import PyMongoError

from common.interface.change_stream_handler import ChangeStreamHandler
from common.config import db_config

class MongoDbChangeStreamHandler(ChangeStreamHandler, ABC):
    def __init__(self, collection_name: str):
        self.client = MongoClient(db_config.MONGODB_URI)
        self.collection = self.client[db_config.MONGODB_DB_NAME][collection_name]

    def listen(self):
        try:
            with self.collection.watch(full_document='updateLookup') as stream:
                print(f"Listening for changes on collection: {self.collection.name}")
                for change in stream:
                    self.dispatch(change)
        except PyMongoError as e:
            print(f"Change stream error: {e}")

    def dispatch(self, change: dict):
        op_type = change.get("operationType")
        if op_type == "insert":
            self.on_insert(change)
        elif op_type == "update":
            self.on_update(change)
