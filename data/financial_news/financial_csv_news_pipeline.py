import os
import logging
from typing import Iterator, Optional
from datetime import datetime, timedelta

from common.interface.data_pipeline import DataPipeline
from common.model.financial_news import FinancialNews
from data.financial_news.financial_csv_news_fetcher import FinancialCsvNewsFetcher
from data.financial_news.financial_csv_news_parser import FinancialCsvNewsParser


class FinancialCsvNewsPipeline(DataPipeline):
    """
    This pipeline is responsible for fetching and parsing financial news data from a CSV file, with support for filtering by time range and ticker.
    """
    
    def __init__(self, csv_path: str, ticker: Optional[str] = None):
        self.csv_path = csv_path
        self.ticker = ticker
        self.parser = FinancialCsvNewsParser()
        self.fetcher = FinancialCsvNewsFetcher(self.parser, self.csv_path, ticker)
        
        # set logger
        self.logger = logging.getLogger(__name__)
    
    def process(self, start_date: str, end_date: str) -> Iterator[FinancialNews]:
        self.logger.info(f"Start processing news data: {start_date} to {end_date}, ticker: {self.ticker or 'all'}")
        
        try:
            # check if file exists
            if not os.path.exists(self.csv_path):
                self.logger.error(f"CSV file does not exist: {self.csv_path}")
                return
            
            # fetch and parse news data
            news_count = 0
            for news in self.fetcher.fetch(start_date, end_date):
                news_count += 1
                yield news
            
            self.logger.info(f"Processing completed, fetched {news_count} news")
            
        except Exception as e:
            self.logger.error(f"Error processing news data: {str(e)}")
            raise
    
    def get_news_by_ticker(self, ticker: str, start_date: str, end_date: str) -> Iterator[FinancialNews]:
        self.logger.info(f"Getting news data for stock {ticker}: {start_date} to {end_date}")
        
        # create new pipeline instance, specify stock code
        pipeline = FinancialCsvNewsPipeline(self.csv_path, ticker)
        return pipeline.process(start_date, end_date)
