import os
import sys
import json
import torch
from torch.serialization import add_safe_globals
import pickle
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
import logging

from common.model.end_of_day import EndOfDayEvent
from common.model.portfolio_result import PortfolioResult
from common.config.db_config import MONGODB_COLLECTION_PORTFOLIO, MONGODB_COLLECTION_OHLC, MONGODB_COLLECTION_NEWS, MONGODB_COLLECTION_SENTIMENT
from common.infrastructure.mongodb.mongodb_client import MongoDbClient
from ml_model.rl_model.agent import RLActor, RLAgent
from ml_model.rl_model.environment.portfolio_env import PortfolioEnv
from ml_model.ml_model_helper import MlModelHelper
from common.config.target_tickers import TARGET_TICKERS
from ml_model.rl_model.utils.parse_config import ConfigParser

class RLModelHandler:
    def __init__(self, model_path: str, config_path: str = None):
        self.model_path = model_path
        self.mongodb = MongoDbClient()
        self.ml_helper = MlModelHelper()
        
        # Set device based on CUDA availability
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"Using device: {self.device}")
        logger = logging.getLogger()
        
        # Load configuration
        if config_path is None:
            config_path = 'ml_model/rl_model/hyper.json'
        
        with open(config_path) as f:
            options = json.load(f)
            self.args = ConfigParser(options)
        self.args.num_assets = 102
                   
        # Load model
        matrix_path = os.path.join('ml_model/rl_model/data', self.args.market, self.args.relation_file)
        try:
            logger.info(f"Loading adjacency matrix from {matrix_path}")
            A = torch.from_numpy(np.load(matrix_path)).float().to(self.device)
        except Exception as e:
            logger.error(f"Error loading adjacency matrix: {str(e)}")
            raise

        # Then load the full model
        supports = [A]
        actor = RLActor(supports, self.args).to(self.device)
        actor.load_state_dict(torch.load(self.model_path, map_location=self.device))
        actor.eval()
        self.model = actor
        # Initialize environment and agent (will be created when data is available)
        self.env = None
        self.agent = None
    
    def _fetch_data_from_mongodb(self, date: str) -> Tuple[np.ndarray, np.ndarray]:
        """Fetch stock data and market data from MongoDB for a specific date"""
        logger = logging.getLogger()
        try:
            # Calculate the required window size
            window_size = (self.args.window_len + 1) * 5  # Same as in DataGenerator._get_data
            
            # Get start and end dates for the window
            end_date = datetime.strptime(date, "%Y-%m-%d")
            delta_days = window_size * 2
            start_date = end_date - timedelta(days=delta_days)
            
            # Initialize data structures
            num_assets = len(TARGET_TICKERS)
            stocks_data = np.zeros((num_assets, window_size, 7))  # 7 features: close, high, low, volume, marketcap, sentiment, sec_score
            market_data = np.zeros((window_size, 5))  # 5 features: close, high, low, volume, marketcap
            
            # First, get all dates from OHLC data
            all_dates = set()
            stock_data_dict = {ticker: [] for ticker in TARGET_TICKERS}
            
            # Fetch OHLC data for all tickers
            for i, ticker in enumerate(TARGET_TICKERS):
                query = {
                    "ticker": ticker,
                    "date": {
                        "$gte": start_date.strftime("%Y-%m-%d"),
                        "$lte": end_date.strftime("%Y-%m-%d")
                    }
                }
                ohlc_docs = list(self.mongodb.find(MONGODB_COLLECTION_OHLC, query))
                
                for doc in ohlc_docs:
                    date = doc['date']
                    all_dates.add(date)
                    stock_data_dict[ticker].append({
                        'date': date,
                        'close': doc['close'],
                        'high': doc['high'],
                        'low': doc['low'],
                        'volume': doc['volume'],
                        'marketcap': doc.get('marketcap', 0.0),
                        'sentiment': 0.0,
                        'sec_score': 0.0
                    })

            # Sort dates and create date index mapping
            all_dates = sorted(list(all_dates))
            if len(all_dates) >= window_size:
                selected_dates = all_dates[-window_size:]
            else:
                logger.warning(f"Not enough data for {ticker}. Expected {window_size} days, got {len(all_dates)} days")
            date_to_idx = {date: idx for idx, date in enumerate(selected_dates)}
            
            # Get sentiment and SEC scores
            sentiment_cache = {}
            sec_cache = {}
            
            # Process sentiment scores
            for ticker in TARGET_TICKERS:
                ticker_dates = [data_point['date'] for data_point in stock_data_dict[ticker]]
                query = {
                    "ticker": ticker,
                    "date": {"$in": ticker_dates}
                }
                sentiment_docs = list(self.mongodb.find(MONGODB_COLLECTION_SENTIMENT, query))
                
                for doc in sentiment_docs:
                    date = doc['date']
                    sentiment_cache[f"{ticker}_{date}"] = doc.get('avg_score', 0.0)
            
            # Process SEC scores
            for ticker in TARGET_TICKERS:
                for data_point in stock_data_dict[ticker]:
                    date = data_point['date']
                    sec_score = self.ml_helper.get_sec_score(ticker, date)
                    sec_cache[f"{ticker}_{date}"] = sec_score
            
            # Update stock data with sentiment and SEC scores
            missing_sentiment_count = 0
            for i, ticker in enumerate(TARGET_TICKERS):
                for data_point in stock_data_dict[ticker]:
                    date = data_point['date']
                    cache_key = f"{ticker}_{date}"
                    
                    # Get sentiment score from cache or use default
                    sentiment_score = sentiment_cache.get(cache_key, 0.0)
                    if sentiment_score == 0.0 and cache_key not in sentiment_cache:
                        missing_sentiment_count += 1
                    data_point['sentiment'] = sentiment_score
                    
                    # Get SEC score from cache or use default
                    data_point['sec_score'] = sec_cache.get(cache_key, 0.0)
            
            if missing_sentiment_count > 0:
                logger.warning(f"Missing sentiment scores for {missing_sentiment_count} ticker-date combinations. Using default value of 0.0")
            
            # Fill stock data array
            for i, ticker in enumerate(TARGET_TICKERS):
                for data_point in stock_data_dict[ticker]:
                    if data_point['date'] in date_to_idx:
                        idx = date_to_idx[data_point['date']]
                        stocks_data[i, idx] = [
                            data_point['close'],
                            data_point['high'],
                            data_point['low'],
                            data_point['volume'],
                            data_point['marketcap'],
                            data_point['sentiment'],
                            data_point['sec_score']
                        ]
            
            # Fetch market data
            market_query = {
                "ticker": "^GSPC",
                "date": {
                    "$gte": start_date.strftime("%Y-%m-%d"),
                    "$lte": end_date.strftime("%Y-%m-%d")
                }
            }
            market_docs = list(self.mongodb.find(MONGODB_COLLECTION_OHLC, market_query))
            market_data_dict = {}
            for doc in market_docs:
                date = doc['date']
                
                if date in date_to_idx:
                    market_data_dict[date] = {
                        'close': doc['close'],
                        'high': doc['high'],
                        'low': doc['low'],
                        'volume': doc['volume'],
                        'marketcap': doc.get('marketcap', 0.0)
                    }
            
            # Fill market data array
            for date, idx in date_to_idx.items():
                if date in market_data_dict:
                    data = market_data_dict[date]
                    market_data[idx] = [
                        data['close'],
                        data['high'],
                        data['low'],
                        data['volume'],
                        data['marketcap']
                    ]
            

            for i, ticker in enumerate(TARGET_TICKERS):
                # Get current day's close price
                current_close = stocks_data[i, -1, 0]

            return stocks_data, market_data
            
        except Exception as e:
            logger.error(f"Error fetching data from MongoDB: {str(e)}")
            raise
    
    def _create_environment(self, stocks_data: np.ndarray, market_data: np.ndarray) -> PortfolioEnv:
        return PortfolioEnv(
            assets_data=stocks_data,
            market_data=market_data,
            in_features=self.args.in_features,
            val_idx=stocks_data.shape[1] - 1,
            test_idx=stocks_data.shape[1] - 1,
            batch_size=1,
            window_len=self.args.window_len,
            trade_len=0,
            max_steps=self.args.max_steps,
            norm_type=self.args.norm_type,
            allow_short=False,
            mode='pred'
        )
    
    def _create_agent(self, env: PortfolioEnv) -> RLAgent:
        agent = RLAgent(env, self.model, self.args)
        agent.set_pred()
        return agent
    
    def process_end_of_day(self, event: EndOfDayEvent) -> None:
        """Process end of day event and save portfolio results"""
        try:
            # Get current date
            date = event.date.strftime("%Y-%m-%d")
            
            # Fetch data from MongoDB
            stocks_data, market_data = self._fetch_data_from_mongodb(date)\
            # Create environment with fetched data
            self.env = self._create_environment(stocks_data, market_data)
            
            # Reset environment
            states = self.env.reset()
            
            # Get model prediction
            with torch.no_grad():
                x_a = torch.from_numpy(states[0]).float().to(self.device)
                weights, rho, _, _ = self.model(x_a, None, deterministic=False)

            # Convert weights to numpy
            if isinstance(weights, torch.Tensor):
                weights_np = weights[0].cpu().numpy()
            else:
                weights_np = weights[0]
            
            # Extract long and short positions
            num_assets = stocks_data.shape[0]
            long_weights = weights_np[:num_assets]
            
            # Normalize long weights to ensure they sum to 1
            long_weights_sum = np.sum(long_weights)
            if long_weights_sum > 0:
                long_weights = long_weights / long_weights_sum
            else:
                long_weights = np.ones(num_assets) / num_assets
            
            # Create portfolio result
            portfolio_result = PortfolioResult(
                tickers=TARGET_TICKERS,
                portfolio_weights=long_weights.tolist(),
                long_ratio=1,
                expected_return=0.0,
                date_index=stocks_data.shape[1] - 1,
                returns=[],
                date=event.date
            )
            
            # Save to MongoDB
            self.mongodb.delete(MONGODB_COLLECTION_PORTFOLIO, {"date": event.date.strftime("%Y-%m-%d")})
            self.mongodb.insert(MONGODB_COLLECTION_PORTFOLIO, portfolio_result.to_dict())

        except Exception as e:
            print(f"Error processing end of day: {str(e)}")
            raise 
        
if __name__ == "__main__":
    # Test RL model
    print("RL MODEL TEST ==================================")
    
    model_path = "ml_model/rl_model/trained_model_file/model_7dim_top20_output/model_file/best_cr-34.pth"  # Path to the trained model
    rl_handler = RLModelHandler(model_path)
    portfolio_result = rl_handler.process_end_of_day(EndOfDayEvent(date="2010-09-04", source="unit_test"))
    print(f"portfolio_result: {portfolio_result}")
    
    print("Test complete.")