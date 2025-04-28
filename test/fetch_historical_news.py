"""
Historical: 2000-01-01 to 2009-12-31
Source: csv/keydev.csv
Ticker List: tickers.json
"""

import os
import json
import logging
from datetime import datetime
from typing import List, Dict, Any
from bson import ObjectId

from common.config.target_tickers import TARGET_TICKERS
from common.infrastructure.mongodb.mongodb_client import MongoDbClient
from common.config.db_config import MONGODB_COLLECTION_NEWS
from data.financial_news.financial_csv_news_pipeline import FinancialCsvNewsPipeline


class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        return super().default(o)


def load_tickers(ticker_file: str) -> List[str]:
    try:
        with open(ticker_file, 'r') as f:
            tickers = json.load(f)
        return tickers
    except Exception as e:
        logging.error(f"Error loading tickers from {ticker_file}: {str(e)}")
        return []


def fetch_historical_news(
    csv_path: str,
    # ticker_file: str,
    start_date: str = "1999-01-01",
    end_date: str = "2015-12-31",
    output_dir: str = "../data/financial_news/csv",
    save_to_mongodb: bool = True
) -> Dict[str, List[Dict[str, Any]]]:
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Load tickers
    # tickers = load_tickers(ticker_file)
    tickers = TARGET_TICKERS
    if not tickers:
        logger.error("No tickers loaded. Exiting.")
        return {}
    
    logger.info(f"Loaded {len(tickers)} tickers ")
    
    # Initialize pipeline
    pipeline = FinancialCsvNewsPipeline(csv_path)
    
    # Initialize MongoDB client if needed
    mongo_client = None
    if save_to_mongodb:
        mongo_client = MongoDbClient()
        # Clear existing data for the date range
        mongo_client.delete(MONGODB_COLLECTION_NEWS, {
            "datetime": {
                "$gte": int(datetime.strptime(start_date, "%Y-%m-%d").timestamp()),
                "$lte": int(datetime.strptime(end_date, "%Y-%m-%d").timestamp())
            }
        })
        logger.info(f"Cleared existing news data in MongoDB for date range {start_date} to {end_date}")
    
    # Dictionary to store results
    results = {}
    
    # Process each ticker
    for ticker in tickers:
        logger.info(f"Processing ticker: {ticker}")
        
        # Get news for this ticker
        news_list = list(pipeline.get_news_by_ticker(ticker, start_date, end_date))
        
        # Convert to dictionary format for JSON serialization
        news_dicts = [news.to_dict() for news in news_list]
        
        # Store results
        results[ticker] = news_dicts
        
        # Save to individual file
        output_file = os.path.join(output_dir, f"{ticker}_news.json")
        with open(output_file, 'w') as f:
            json.dump(news_dicts, f, indent=2, cls=JSONEncoder)
        
        logger.info(f"Saved {len(news_dicts)} news items for {ticker} to {output_file}")
        
        # Save to MongoDB if enabled
        if save_to_mongodb and news_dicts:
            # Add source metadata
            for news in news_dicts:
                news["source"] = "keydev.csv"
            
            # Insert into MongoDB
            mongo_client.insert_many(MONGODB_COLLECTION_NEWS, news_dicts)
            logger.info(f"Saved {len(news_dicts)} news items for {ticker} to MongoDB")
    
    # Save combined results
    combined_file = os.path.join(output_dir, "all_historical_news.json")
    with open(combined_file, 'w') as f:
        json.dump(results, f, indent=2, cls=JSONEncoder)
    
    logger.info(f"Saved combined results to {combined_file}")
    
    # Verify MongoDB data
    if save_to_mongodb:
        total_count = mongo_client.count_documents(MONGODB_COLLECTION_NEWS, {})
        logger.info(f"Total news items in MongoDB: {total_count}")
    
    return results


def main():
    """Main function to run the script"""
    # Define paths
    # script_dir = os.path.dirname(os.path.abspath(__file__))
    # base_dir = os.path.dirname(script_dir)
    # csv_path = os.path.join(base_dir, "data", "financial_news", "csv", "keydev.csv")
    csv_path = "/home/newstraderrl/data/news/keydev.csv"
    # ticker_file = os.path.join(script_dir, "tickers.json")
    # output_dir = os.path.join(base_dir, "data", "financial_news", "csv", "historical_news")
    output_dir = "/home/newstraderrl/data/news/output/"
    # Fetch historical news and save to MongoDB
    fetch_historical_news(
        csv_path=csv_path,
        # ticker_file=ticker_file,
        output_dir=output_dir,
        save_to_mongodb=True
    )


if __name__ == "__main__":
    main()