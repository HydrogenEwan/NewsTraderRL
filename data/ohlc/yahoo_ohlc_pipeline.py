from common.config.db_config import MONGODB_COLLECTION_OHLC
from common.infrastructure.mongodb.mongodb_client import MongoDbClient
from common.interface.data_pipeline import DataPipeline
from data.ohlc.yahoo_ohlc_parser import YahooOhlcParser
from data.ohlc.yahoo_ohlc_fetcher import YahooOhlcFetcher


class YahooOhlcPipeline(DataPipeline):
    def __init__(self):
        super().__init__()

    def run_historical_pipeline(self, ticker: str, start: str, end: str, batch_size: int = 100):
        parser = YahooOhlcParser(ticker)
        fetcher = YahooOhlcFetcher(ticker, parser)

        for batch in self.batch_iterator(fetcher.fetch(start, end), batch_size):
            self.client.insert_many(MONGODB_COLLECTION_OHLC, [x.to_dict() for x in batch])

    def run_simulation_pipeline(self, ticker: str, start: str, end: str, batch_size: int = 100):
        parser = YahooOhlcParser(ticker)
        fetcher = YahooOhlcFetcher(ticker, parser)

        for batch in self.batch_iterator(fetcher.fetch(start, end), batch_size):
            for ohlc in batch:
                self.upsert_simulation_data(
                    simulation_date=ohlc.date,
                    data_type=MONGODB_COLLECTION_OHLC,
                    new_data=ohlc.to_dict()
                )


if __name__ == "__main__":
    pipeline = YahooOhlcPipeline()

    # test for historical pipeline

    # pipeline.run_historical_pipeline(
    #     ticker="AAPL",
    #     start="2024-01-01",
    #     end="2024-03-31",
    #     batch_size=100
    # )

    # client = MongoDbClient()
    # # deleted_many = client.delete("ohlc", {"ticker": "AAPL"})
    # docs = list(client.find("ohlc"))
    # print("[INFO] Total documents in ohlc:", len(docs))
    # for doc in docs:
    #     print(doc)

    # test for simulation pipeline
    pipeline.run_simulation_pipeline(
        ticker="AAPL",
        start="2024-01-01",
        end="2024-01-03",
        batch_size=100
    )

    client = MongoDbClient()
    docs = list(client.find("simulation", {"items.data_type": "ohlc"}))
    print("[INFO] Total simulation documents with ohlc:", len(docs))
    for doc in docs:
        print(doc)
    # result
    # {'_id': ObjectId('6801c167bb8392559138b7c2'), 'date': datetime.datetime(2024, 1, 2, 5, 0), 'items': [{'data_type': 'ohlc', 'data': [{'ticker': 'AAPL', 'date': datetime.datetime(2024, 1, 2, 5, 0), 'open': 186.03307200647276, 'high': 187.31538170646215, 'low': 182.79253333369908, 'close': 184.53208923339844, 'volume': 82488700}]}]}