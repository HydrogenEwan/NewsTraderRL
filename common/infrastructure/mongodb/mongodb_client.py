from pymongo import MongoClient
from pymongo.collection import Collection
from typing import Union, List, Dict, Optional
from common.config import db_config


class MongoDbClient:
    def __init__(self):
        self._client = MongoClient(db_config.MONGODB_URI)
        self._db = self._client[db_config.MONGODB_DB_NAME]

    def get_collection(self, collection_name: str) -> Collection:
        return self._db[collection_name]

    def insert(self, collection_name: str, data: Dict) -> Optional[str]:
        collection = self.get_collection(collection_name)

        if not isinstance(data, dict):
            raise ValueError("insert() only accepts a single document as a dict.")

        try:
            result = collection.insert_one(data)
            return str(result.inserted_id)
        except Exception as e:
            print(f"[MongoDbClient] insert failed: {e}")
            return None

    def insert_many(self, collection_name: str, data_list: List[Dict]) -> Optional[List[str]]:
        collection = self.get_collection(collection_name)
        try:
            result = collection.insert_many(data_list)
            return [str(_id) for _id in result.inserted_ids]
        except Exception as e:
            print(f"[MongoDbClient] insert_many failed: {e}")
            return []

    def replace_one(self, collection_name: str, filter: dict, new_doc: dict):
        collection = self.get_collection(collection_name)
        return collection.replace_one(filter, new_doc, upsert=True)

    def find(self, collection_name: str, filter: dict = None, projection: dict = None, sort: list = None, limit: int = 0):
        collection = self.get_collection(collection_name)
        cursor = collection.find(filter or {}, projection)
        if sort:
            cursor = cursor.sort(sort)
        if limit > 0:
            cursor = cursor.limit(limit)
        return cursor

    def find_one(self, collection_name: str, filter: dict) -> Optional[dict]:
        collection = self.get_collection(collection_name)
        return collection.find_one(filter)

    def delete(self, collection_name: str, filter: dict) -> int:
        collection = self.get_collection(collection_name)
        try:
            result = collection.delete_many(filter)
            return result.deleted_count
        except Exception as e:
            print(f"[MongoDbClient] delete_many failed: {e}")
            return 0

    def count_documents(self, collection_name: str, filter: dict) -> int:
        collection = self.get_collection(collection_name)
        try:
            return collection.count_documents(filter)
        except Exception as e:
            print(f"[MongoDbClient] count_documents failed: {e}")
            return 0