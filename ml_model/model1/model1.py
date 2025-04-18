from common.infrastructure.mongodb.mongodb_change_stream_handler import MongoDbChangeStreamHandler
from common.config import db_config

class Model1Handler(MongoDbChangeStreamHandler):
    def __init__(self):
        super().__init__(db_config.MONGODB_COLLECTION_NEWS)

    def on_insert(self, change: dict):
        doc = change["fullDocument"]
        print("[Model1] Insert event:", doc)