import yfinance as yf
import pandas as pd
from typing import Iterator
from datetime import datetime, timedelta


from common.interface.data_fetcher import DataFetcher
from common.interface.data_parser import DataParser
from common.model.ohlc import Ohlc

class YahooOhlcFetcher(DataFetcher):
    def __init__(self, ticker: str, parser: DataParser):
        self.ticker = ticker
        self.parser = parser

    def fetch(self, start: str, end: str) -> Iterator[Ohlc]:
        end_date = datetime.strptime(end, "%Y-%m-%d")  # 문자열 → datetime
        next_day = end_date + timedelta(days=1)  # 하루 추가
        next_day_str = next_day.strftime("%Y-%m-%d")
        if self.ticker is None:
            raise RuntimeError("ticker not set")

        df = yf.Ticker(self.ticker).history(start=start, end=next_day_str, interval="1d")
        if df.empty:
            return

        df.reset_index(inplace=True)
        for _, row in df.iterrows():
            yield self.parser.parse(row)
