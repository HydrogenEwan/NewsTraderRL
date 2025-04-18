import yfinance as yf
import pandas as pd
from typing import Iterator

from common.interface.data_fetcher import DataFetcher
from common.interface.data_parser import DataParser
from common.model.ohlc import Ohlc

class YahooOhlcFetcher(DataFetcher):
    def __init__(self, ticker: str, parser: DataParser):
        self.ticker = ticker
        self.parser = parser

    def fetch(self, start: str, end: str) -> Iterator[Ohlc]:
        if self.ticker is None:
            raise RuntimeError("ticker not set")

        df = yf.Ticker(self.ticker).history(start=start, end=end, interval="1d")
        if df.empty:
            return

        df.reset_index(inplace=True)
        for _, row in df.iterrows():
            yield self.parser.parse(row)
