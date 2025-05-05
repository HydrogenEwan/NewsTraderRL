from typing import Iterator, Optional
import os
import json
from datetime import datetime

from common.config.db_config import MONGODB_COLLECTION_NEWS
from common.config.financial_news_config import FINNHUB_API_KEY
from common.infrastructure.mongodb.mongodb_client import MongoDbClient
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
        self.mongodb = MongoDbClient()
        self.collection = MONGODB_COLLECTION_NEWS
        
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

            news_dict_list = []
            for news in news_list:
                news_dict_list.append(news.to_dict())

            self.save_to_db(news_dict_list, ticker, start_time, end_time)
            # save news data
            # filepath = self.save_news(news_list, ticker, start_time, end_time)
            # print(f"saved {len(news_list)} news to {filepath}")
            
            # return filepath

            
        except Exception as e:
            print(f"failed to process news data: {e}")
            return None

    def save_to_db(self, news_list: list, ticker: str, start_time: str, end_time: str):
        self.mongodb.delete(self.collection, {
            "ticker": ticker,
            "date": {
                "$gte": start_time,
                "$lte": end_time
            }
        })

        self.mongodb.insert_many(self.collection, news_list)
        # print(f"News saved {len(news_list)} news to db for {ticker}")

    def run_tickers(self, ticker_list: list, start_time: str, end_time: str):
        for t in ticker_list:
            self.run(t, start_time, end_time)


if __name__ == "__main__":
    api = FinancialApiNewsPipeline(FINNHUB_API_KEY)
    api.run("AAPL", "2023-03-01", "2023-03-03")
