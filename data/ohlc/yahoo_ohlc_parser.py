import pandas as pd
from common.interface.data_parser import DataParser
from common.model.ohlc import Ohlc


class YahooOhlcParser(DataParser):
    def __init__(self, ticker: str):
        self.ticker = ticker

    def parse(self, row: pd.Series) -> Ohlc:
        return Ohlc(
            ticker=self.ticker,
            date=row["Date"].to_pydatetime(),
            open=float(row["Open"]),
            high=float(row["High"]),
            low=float(row["Low"]),
            close=float(row["Close"]),
            volume=int(row["Volume"])
        )
