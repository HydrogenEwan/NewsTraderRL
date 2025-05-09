import requests
from typing import Iterator
from datetime import datetime

from common.interface.data_fetcher import DataFetcher
from common.interface.data_parser import DataParser
from common.model.ohlc import Ohlc

class PolygonOhlcFetcher(DataFetcher):
    def __init__(self, ticker: str, parser: DataParser, api_key: str):
        self.ticker = ticker
        self.parser = parser
        self.api_key = api_key

    def fetch(self, start: str, end: str) -> Iterator[Ohlc]:
        """
        start, end: "YYYY-MM-DD"
        """
        url = (
            f"https://api.polygon.io/v2/aggs/ticker/{self.ticker}"
            f"/range/1/day/{start}/{end}"
            f"?adjusted=true&sort=asc&limit=5000&apiKey={self.api_key}"
        )
        resp = requests.get(url)
        resp.raise_for_status()
        data = resp.json()

        # "results" 안에 [{o,h,l,c,v,t,n}, ...] 배열
        for bar in data.get("results", []):
            yield self.parser.parse(bar)
