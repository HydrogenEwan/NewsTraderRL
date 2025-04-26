import yfinance as yf
import pandas as pd
from typing import Iterator
from common.interface.data_fetcher import DataFetcher
from common.model.ohlc import Ohlc

class YahooOhlcFetcher(DataFetcher):
    def __init__(self, ticker: str, parser):
        self.ticker = ticker
        self.parser = parser

    def fetch(self, start: str, end: str) -> Iterator[Ohlc]:
        if not self.ticker:
            raise RuntimeError("ticker not set")

        ticker_obj = yf.Ticker(self.ticker)
        info = ticker_obj.info
        current_shares = info.get("sharesOutstanding", None)
        splits = ticker_obj.splits if hasattr(ticker_obj, 'splits') else pd.Series()

        df = ticker_obj.history(start=start, end=end, interval="1d")
        if df.empty:
            return

        df.reset_index(inplace=True)
        for _, row in df.iterrows():
            # Calculate historical shares outstanding adjusted for splits
            row_date = row["Date"].to_pydatetime().date()
            hist_shares = current_shares
            if current_shares and not splits.empty:
                # splits: Series indexed by date of split, values are split ratios
                splits_after = splits[splits.index.date > row_date]
                try:
                    cum_factor = splits_after.product()
                    hist_shares = current_shares / cum_factor if cum_factor else current_shares
                except Exception:
                    hist_shares = current_shares
            # Compute marketcap at historical date
            marketcap = hist_shares * float(row["Close"]) if hist_shares else None
            yield self.parser.parse(row, marketcap)