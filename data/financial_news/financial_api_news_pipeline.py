from typing import Iterator, Optional
import os
import json
from datetime import datetime
from data.financial_news.financial_api_news_fetcher import FinancialApiNewsFetcher
from data.financial_news.financial_api_news_parser import FinancialApiNewsParser
from common.model.financial_news import FinancialNews

class FinancialApiNewsPipeline:
    def __init__(self, api_key: str, output_dir: str = "data/financial_news/api_news"):
        """
        initialize news processing pipeline
        
        Args:
            api_key: Finnhub API key
            output_dir: output directory, default is data/financial_news/api_news
        """
        self.api_key = api_key
        self.output_dir = output_dir
        self.parser = FinancialApiNewsParser()
        
        # ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
    def process(self, ticker: str, start_time: str, end_time: str) -> Iterator[FinancialNews]:
        """
        process news data in a specified time range
        
        Args:
            ticker: stock code
            start_time: start time, format is YYYY-MM-DD
            end_time: end time, format is YYYY-MM-DD
            
        Returns:
            Iterator[FinancialNews]: news data iterator
        """
        # create news fetcher
        fetcher = FinancialApiNewsFetcher(self.parser, self.api_key, ticker)
        
        # fetch and process news data
        for news in fetcher.fetch(start_time, end_time):
            if news:
                yield news
                
    def save_news(self, news_list: list, ticker: str, start_time: str, end_time: str) -> str:
        """
        save news data to file
        
        Args:
            news_list: news data list
            ticker: stock code
            start_time: start time
            end_time: end time
            
        Returns:
            str: saved file path
        """
        # generate filename
        filename = f"{ticker}_{start_time}_{end_time}.json"
        filepath = os.path.join(self.output_dir, filename)
        
        # convert to dictionary list
        news_dict_list = [news.to_dict() for news in news_list]
        
        # save to file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(news_dict_list, f, ensure_ascii=False, indent=2)
            
        return filepath
        
    def run(self, ticker: str, start_time: str, end_time: str) -> Optional[str]:
        """
        run complete news processing pipeline
        
        Args:
            ticker: stock code
            start_time: start time, format is YYYY-MM-DD
            end_time: end time, format is YYYY-MM-DD
            
        Returns:
            Optional[str]: saved file path, return None if processing fails
        """
        try:
            # fetch news data
            news_list = list(self.process(ticker, start_time, end_time))
            
            if not news_list:
                print(f"no news found for {ticker} from {start_time} to {end_time}")
                return None
                
            # save news data
            filepath = self.save_news(news_list, ticker, start_time, end_time)
            print(f"saved {len(news_list)} news to {filepath}")
            
            return filepath
            
        except Exception as e:
            print(f"failed to process news data: {e}")
            return None
