"""
Simulation: 2022-01-01 to 2024-12-31
Source: finnhub api - company news
Ticker List: tickers.json
"""

import os
import json
import logging
from datetime import datetime
from dotenv import load_dotenv
import sys

# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.financial_news.financial_api_news_pipeline import FinancialApiNewsPipeline

# configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# load environment variables from .env file
load_dotenv()

def load_tickers(ticker_file: str) -> list:
    """
    load stock ticker list from file
    
    Args:
        ticker_file: ticker list file path
        
    Returns:
        list: stock ticker list
    """
    try:
        with open(ticker_file, 'r', encoding='utf-8') as f:
            tickers = json.load(f)
        logger.info(f"successfully loaded {len(tickers)} stock tickers")
        return tickers
    except Exception as e:
        logger.error(f"failed to load stock tickers: {e}")
        return []

def fetch_simulation_news(api_key: str, tickers: list, start_date: str, end_date: str, output_dir: str = "data/financial_news/simulation"):
    """
    fetch simulation news data
    
    Args:
        api_key: Finnhub API key
        tickers: stock ticker list
        start_date: start date (YYYY-MM-DD)
        end_date: end date (YYYY-MM-DD)
        output_dir: output directory
    """
    # create news processing pipeline
    pipeline = FinancialApiNewsPipeline(api_key, output_dir)
    
    # ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # process each stock ticker
    for ticker in tickers:
        try:
            logger.info(f"processing {ticker} news data...")
            filepath = pipeline.run(ticker, start_date, end_date)
            
            if filepath:
                logger.info(f"successfully saved {ticker} news data to {filepath}")
            else:
                logger.warning(f"no news data found for {ticker}")
                
        except Exception as e:
            logger.error(f"failed to process {ticker} news data: {e}")
            continue

def main():
    # configure parameters
    API_KEY = os.getenv("FINNHUB_API_KEY")
    if not API_KEY:
        logger.error("FINNHUB_API_KEY environment variable not set")
        return
        
    TICKER_FILE = os.path.join(os.path.dirname(__file__), "test_tickers.json")
    START_DATE = "2024-12-30"
    END_DATE = "2024-12-31"
    OUTPUT_DIR = "data/financial_news/csv/simulation_api_news"
    
    # load stock tickers
    tickers = load_tickers(TICKER_FILE)
    if not tickers:
        return
        
    # fetch news data
    fetch_simulation_news(API_KEY, tickers, START_DATE, END_DATE, OUTPUT_DIR)
    
if __name__ == "__main__":
    main()
