from __future__ import annotations
from pymongo import MongoClient
from pymongo.collection import Collection
from typing import Union, List, Dict, Optional, Any
from common.config import db_config


class MongoDbClient:
    _instance: Optional[MongoDbClient] = None

    def __init__(self):
        self._client = MongoClient(db_config.MONGODB_URI)
        self._db = self._client[db_config.MONGODB_DB_NAME]

    @classmethod
    def get_instance(cls) -> MongoDbClient:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

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

    def aggregate(
        self,
        collection_name: str,
        pipeline: List[Dict[str, Any]],
        allow_disk_use: bool = False
    ) -> Optional[List[Dict[str, Any]]]:

        collection = self.get_collection(collection_name)
        try:
            cursor = collection.aggregate(pipeline, allowDiskUse=allow_disk_use)
            return list(cursor)
        except Exception as e:
            print(f"[MongoDbClient] aggregate failed: {e}")
            return None

    def get_latest_date(self, collection_name: str) -> Optional[str]:
        try:
            result = self.find(
                collection_name=collection_name,
                sort=[("date", -1)],
                limit=1,
                projection={"date": 1, "_id": 0}
            )
            latest = next(result, None)
            return latest.get("date") if latest else None
        except Exception as e:
            print(f"[MongoDbClient] get_latest_date failed: {e}")
            return None