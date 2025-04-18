import requests
from typing import Iterator
from common.interface.data_fetcher import DataFetcher
from common.interface.data_parser import DataParser


class FinnhubNewsFetcher(DataFetcher):
    def __init__(self, parser: DataParser, token: str, ticker: str):
        self.parser = parser
        self.token = token
        self.ticker = ticker

    def fetch(self, start: str, end: str) -> Iterator:
        url = f"https://finnhub.io/api/v1/company-news?symbol={self.ticker}&from={start}&to={end}&token={self.token}"
        response = requests.get(url)
        response.raise_for_status()
        for item in response.json():
            yield self.parser.parse(item)