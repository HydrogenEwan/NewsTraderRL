import pandas as pd
from typing import Iterator
from common.interface.data_fetcher import DataFetcher
from common.interface.data_parser import DataParser
from common.model.financial_news import FinancialNews


class FinancialCsvNewsFetcher(DataFetcher):
    def __init__(self, parser: DataParser, csv_path: str, ticker: str = None):
        self.parser = parser
        self.csv_path = csv_path
        self.ticker = ticker

    def fetch(self, start: str, end: str) -> Iterator[FinancialNews]:
        # read CSV file
        df = pd.read_csv(self.csv_path)
        
        # convert datetime string to timestamp
        df['datetime'] = pd.to_datetime(df['datetime']).astype('int64') // 10**9
        
        # convert start and end to timestamps
        start_ts = int(pd.to_datetime(start).timestamp())
        end_ts = int(pd.to_datetime(end).timestamp())
        
        # filter time range
        mask = (df['datetime'] >= start_ts) & (df['datetime'] <= end_ts)
        df = df[mask]
        
        # if ticker is specified, filter specific stock
        if self.ticker:
            df = df[df['ticker'] == self.ticker]
        
        if df.empty:
            return

        # iterate data and parse
        for _, row in df.iterrows():
            news_dict = row.to_dict()
            news = self.parser.parse(news_dict)
            if news:
                yield news
