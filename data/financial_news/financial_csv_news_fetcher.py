import pandas as pd
from typing import Iterator
from common.interface.data_fetcher import DataFetcher
from common.interface.data_parser import DataParser
from common.model.financial_news import FinancialNews


class FinancialCsvNewsFetcher(DataFetcher):
    def __init__(self, parser: DataParser, csv_path: str,
                 ticker: str | None = None,
                 chunksize: int = 500_000):
        self.parser = parser
        self.csv_path = csv_path
        self.ticker = ticker
        self.chunksize = chunksize

    def fetch(self, start: str, end: str) -> Iterator[FinancialNews]:
        start_ts = int(pd.to_datetime(start).timestamp())
        end_ts   = int(pd.to_datetime(end).timestamp())

        colnames = ["id", "ticker", "news_id",
                    "datetime", "headline", "summary"]
        for chunk in pd.read_csv(
                self.csv_path,
                header=None,
                names=colnames,
                chunksize=self.chunksize,
                quoting=1, escapechar="\\",
                encoding="utf-8",
                memory_map=True
        ):
            if "datetime" in chunk.columns:
                s = chunk["datetime"]
            elif "date" in chunk.columns:
                s = chunk["date"]
            elif "timestamp" in chunk.columns:
                s = chunk["timestamp"]
            else:
                raise ValueError(
                    "CSV date error"
                )

            chunk["datetime"] = pd.to_datetime(s).astype("int64") // 10**9

            mask = chunk["datetime"].between(start_ts, end_ts)
            if self.ticker:
                mask &= chunk["ticker"] == self.ticker
            sub = chunk[mask]

            if sub.empty:
                continue

            for _, row in sub.iterrows():
                news = self.parser.parse(row.to_dict())
                if news:
                    yield news
