from typing import Iterator
import pandas as pd
from datetime import datetime
import finnhub
from common.interface.data_fetcher import DataFetcher
from common.interface.data_parser import DataParser
from common.model.financial_news import FinancialNews

class FinancialApiNewsFetcher(DataFetcher):
    def __init__(self, parser: DataParser, api_key: str, ticker: str = None):
        self.parser = parser
        self.api_key = api_key
        self.ticker = ticker
        self.client = finnhub.Client(api_key=api_key)
        
    def fetch(self, start: str, end: str) -> Iterator[FinancialNews]:
        if not self.ticker:
            raise ValueError("must specify ticker when using Finnhub API")
            
        # get news data
        news_list = self.client.company_news(
            self.ticker,
            _from=start,
            to=end
        )
        
        if not news_list:
            return
            
        # convert response data to DataFrame
        df = pd.DataFrame(news_list)
        
        # iterate data and parse
        for _, row in df.iterrows():
            news_dict = row.to_dict()
            news = self.parser.parse(news_dict)
            if news:
                yield news
