import threading
import time

from common.config.db_config import MONGODB_COLLECTION_OHLC
from common.infrastructure.mongodb.mongodb_change_stream_handler import MongoDbChangeStreamHandler
from data.ohlc.yahoo_ohlc_pipeline import YahooOhlcPipeline


def on_insert(change: dict):
    print(f"New document inserted: {change['fullDocument']}")

def push_test():
    pipeline = YahooOhlcPipeline()
    pipeline.run_historical_pipeline(
        ticker="AAPL",
        start="2020-01-01",
        end="2020-01-20",
        batch_size=1
    )


if __name__ == "__main__":
    change_stream_handler = MongoDbChangeStreamHandler(MONGODB_COLLECTION_OHLC)
    change_stream_handler.on_insert = on_insert

    t = threading.Thread(target=push_test)
    t.start()

    change_stream_handler.listen()