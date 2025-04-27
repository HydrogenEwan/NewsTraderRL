from abc import ABC, abstractmethod
from itertools import islice
from datetime import date

from common.config.db_config import MONGODB_COLLECTION_SIMULATION
from common.infrastructure.mongodb.mongodb_client import MongoDbClient
from common.model.simulation import Simulation, SimulationItem


class DataPipeline(ABC):
    def __init__(self):
        self.client = MongoDbClient()

    def batch_iterator(self, iterator, batch_size):
        while True:
            batch = list(islice(iterator, batch_size))
            if not batch:
                break
            yield batch

    def upsert_simulation_data(self, simulation_date: date, data_type: str, new_data: dict):
        collection = MONGODB_COLLECTION_SIMULATION
        existing_doc = self.client.find_one(collection, {"date": simulation_date})

        if not existing_doc:
            sim = Simulation(
                date=simulation_date,
                items=[SimulationItem(data_type=data_type, data=[new_data])]
            )
            self.client.insert(collection, sim.to_dict())
            return

        items = existing_doc.get("items", [])
        updated = False
        for item in items:
            if item["data_type"] == data_type:
                if not isinstance(item["data"], list):
                    item["data"] = [item["data"]]
                item["data"].append(new_data)
                updated = True
                break

        if not updated:
            items.append({"data_type": data_type, "data": [new_data]})

        self.client.replace_one(collection, {"date": simulation_date}, {
            "date": simulation_date,
            "items": items
        })
