from datetime import date, timedelta, datetime
from common.infrastructure.mongodb.mongodb_client import MongoDbClient
from common.config.db_config import MONGODB_COLLECTION_NEWS
from common.interface.data_pipeline import DataPipeline
from finnhub import Client
import time

class FinnhubNewsPipeline(DataPipeline):
    def __init__(self, api_key: str):
        super().__init__()
        self.finnhub_client = Client(api_key=api_key)

    def run_historical_pipeline(self, ticker: str, start: str, end: str, batch_days: int = 30,
                                max_calls_per_day: int = 1000, call_counter: list = None):
        start_date = datetime.strptime(start, "%Y-%m-%d").date()
        end_date = datetime.strptime(end, "%Y-%m-%d").date()
        current_date = start_date

        while current_date <= end_date:
            if call_counter is not None and call_counter[0] >= max_calls_per_day:
                print(f"[STOP] Reached daily API limit ({max_calls_per_day})")
                return

            from_date = current_date
            to_date = current_date + timedelta(days=batch_days - 1)
            if to_date > end_date:
                to_date = end_date

            try:
                news_batch = self.finnhub_client.company_news(
                    ticker, _from=from_date.isoformat(), to=to_date.isoformat()
                )
                for news in news_batch:
                    news["ticker"] = ticker
                    news["from_date"] = from_date.isoformat()
                    news["to_date"] = to_date.isoformat()

                if news_batch:
                    self.client.insert_many(MONGODB_COLLECTION_NEWS, news_batch)
                    print(f"[INFO] Inserted {len(news_batch)} news items for {ticker} ({from_date} ~ {to_date})")
                else:
                    print(f"[INFO] No news for {ticker} ({from_date} ~ {to_date})")

                query = {
                    "ticker": ticker,
                    "from_date": from_date.isoformat(),
                    "to_date": to_date.isoformat()
                }
                inserted_count = self.client.count_documents(MONGODB_COLLECTION_NEWS, query)
                print(f"[VERIFY] Found {inserted_count} documents for {ticker} in DB ({from_date} ~ {to_date})")

            except Exception as e:
                print(f"[ERROR] {ticker} ({from_date} ~ {to_date}): {e}")
                time.sleep(5)

            if call_counter is not None:
                call_counter[0] += 1

            current_date += timedelta(days=batch_days)
            time.sleep(1)


if __name__ == '__main__':
    TICKERS = [
        "AAPL", "ABBV", "ABT", "ACN", "ADBE", "AIG", "AMD", "AMGN", "AMT", "AMZN",
        "AVGO", "AXP", "BA", "BAC", "BK", "BKNG", "BLK", "BMY", "BRK.B", "C",
        "CAT", "CHTR", "CL", "CMCSA", "COF", "COP", "COST", "CRM", "CSCO", "CVS",
        "CVX", "DE", "DHR", "DIS", "DUK", "EMR", "FDX", "GD", "GE", "GILD",
        "GM", "GOOG", "GOOGL", "GS", "HD", "HON", "IBM", "INTC", "INTU", "ISRG",
        "JNJ", "JPM", "KO", "LIN", "LLY", "LMT", "LOW", "MA", "MCD", "MDLZ",
        "MDT", "MET", "META", "MMM", "MO", "MRK", "MS", "MSFT", "NEE", "NFLX",
        "NKE", "NOW", "NVDA", "ORCL", "PEP", "PFE", "PG", "PLTR", "PM", "PYPL",
        "QCOM", "RTX", "SBUX", "SCHW", "SO", "SPG", "T", "TGT", "TMO", "TMUS",
        "TSLA", "TXN", "UNH", "UNP", "UPS", "USB", "V", "VZ", "WFC", "WMT", "XOM"
    ]

    pipeline = FinnhubNewsPipeline(api_key="d00hff9r01qk939o4ni0d00hff9r01qk939o4nig")

    pipeline.client.delete(MONGODB_COLLECTION_NEWS, {})
    count = pipeline.client.count_documents(MONGODB_COLLECTION_NEWS, {})
    print(f"[INFO] Deleted all documents in {MONGODB_COLLECTION_NEWS}. Remaining: {count}")

    call_counter = [0]

    for ticker in TICKERS:
        pipeline.run_historical_pipeline(
            ticker,
            start="2024-04-18",
            end="2025-04-18",
            batch_days=365,
            max_calls_per_day=1000,
            call_counter=call_counter
        )

    print(f"\nFinished. Total API calls made: {call_counter[0]}")