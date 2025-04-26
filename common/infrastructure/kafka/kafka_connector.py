import threading
import time
from datetime import date

from common.config.kafka_config import KAFKA_CONNECTOR_PREFIX
from common.infrastructure.kafka.kafka_client import KafkaClient
from common.infrastructure.mongodb.mongodb_client import MongoDbClient
from common.model.ohlc import Ohlc


class KafkaConnector:
    def __init__(self):
        self.kafka = KafkaClient()
        self.mongodb = MongoDbClient()
        self.counter = 0

    def start(self):
        self.kafka.listen_db(KAFKA_CONNECTOR_PREFIX, self._handle_message)

    def _handle_message(self, topic:str, data:dict):
        # print(f"Received message from topic {topic}: {data}")
        # print (isinstance(data, dict))
        self.mongodb.insert(topic, data)
        self.counter += 1
        if self.counter % 10 == 0:
            print(f"Processed {self.counter} messages")




if __name__ == "__main__":
    connector = KafkaConnector()

    # Background producer: every second, create and push an Ohlc object
    # def produce_ohlc():
    #     while True:
    #         sample = Ohlc(
    #             ticker='AAPL',
    #             date=date.today(),
    #             open=100.0,
    #             high=110.0,
    #             low=90.0,
    #             close=105.0,
    #             volume=1000,
    #             marketcap=1e12
    #         )
    #         # Push to Kafka using the DB method
    #         connector.kafka.push_db(KAFKA_CONNECTOR_PREFIX, sample)
    #         time.sleep(1)
    #
    # producer_thread = threading.Thread(target=produce_ohlc, daemon=True)
    # producer_thread.start()

    # Start the connector listener (blocks main thread)
    connector.start()
