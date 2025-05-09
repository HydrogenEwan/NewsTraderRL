import time
from common.config.db_config import MONGODB_COLLECTION_OHLC
from common.config.polygon_config import POLYGON_API_KEY
from common.config.target_tickers import TARGET_TICKERS
from common.infrastructure.mongodb.mongodb_client import MongoDbClient
from common.interface.data_pipeline import DataPipeline
from data.ohlc.polygon_ohlc_fetcher import PolygonOhlcFetcher
from data.ohlc.polygon_ohlc_parser import PolygonOhlcParser

class PolygonOhlcPipeline(DataPipeline):
    def __init__(self):
        super().__init__()
        self.api_key = POLYGON_API_KEY

    def run_pipeline(
        self,
        ticker: str,
        start: str,
        end: str,
        batch_size: int = 100,
        collection: str = MONGODB_COLLECTION_OHLC
    ):
        parser = PolygonOhlcParser(ticker)
        fetcher = PolygonOhlcFetcher(ticker, parser, api_key=self.api_key)
        mongodb = MongoDbClient()

        # 기존 범위 삭제
        mongodb.delete(collection, {
            "ticker": ticker,
            "date": {
                "$gte": start,
                "$lte": end
            }
        })

        # 페치 & 배치 인서트
        for batch in self.batch_iterator(fetcher.fetch(start, end), batch_size):
            docs = [x.to_dict() for x in batch]
            self.client.insert_many(collection, docs)

if __name__ == "__main__":
    start = "2024-01-01"
    end = "2025-04-30"
    ticker_list = TARGET_TICKERS
    ticker_list.append("^GSPC")
    ticker_list.append("^VIX")

    pipeline = PolygonOhlcPipeline()
    for t in ticker_list:
        print(f"[INFO] Running simulation for MarketData {t}")
        pipeline.run_pipeline(ticker=t, start=start, end=end, collection=MONGODB_COLLECTION_OHLC)
        if t == "AAPL":
            break