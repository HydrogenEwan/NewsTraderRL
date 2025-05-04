import os
import sys
import json
import torch
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
        supports = [A]
        self.model = RLActor(supports, self.args).to(self.device)
        self.model = torch.load(self.model_path, map_location=self.device, weights_only=False)
        self.model.to(self.device)  # Ensure model is on the correct device
        
        for name, param in self.model.named_parameters():
            print(f"{name}: {param.shape}, mean={param.data.mean():.4f}, std={param.data.std():.4f}")

        print(f"Model loaded from {self.model_path}")
        self.model.eval()  # Set to evaluation mode
        
        # Initialize environment and agent (will be created when data is available)
        self.env = None
        self.agent = None
    
    def _fetch_data_from_mongodb(self, date: str) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Fetch stock data, market data, and sentiment scores from MongoDB for a specific date"""
        logger = logging.getLogger()
        try:
            # Calculate the required window size
            window_size = (self.args.window_len + 1) * 5  # Same as in DataGenerator._get_data
            
            # Get start and end dates for the window
            end_date = datetime.strptime(date, "%Y-%m-%d")
            start_date = end_date - timedelta(days=window_size)
            
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
            date_to_idx = {date: idx for idx, date in enumerate(all_dates)}
            
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
            
            # Calculate returns for the window
            window_returns = np.zeros((num_assets, window_size))
            for i in range(num_assets):
                for j in range(1, window_size):
                    if stocks_data[i, j-1, 0] > 0:  # Check if previous close price exists
                        window_returns[i, j] = (stocks_data[i, j, 0] - stocks_data[i, j-1, 0]) / stocks_data[i, j-1, 0]
            
            # Get current day's returns
            current_returns = np.zeros(num_assets)
            for i, ticker in enumerate(TARGET_TICKERS):
                # Get current day's close price
                current_close = stocks_data[i, -1, 0]
                # Get previous day's close price
                if window_size > 1 and stocks_data[i, -2, 0] > 0:
                    prev_close = stocks_data[i, -2, 0]
                    current_returns[i] = (current_close - prev_close) / prev_close
                else:
                    current_returns[i] = 0.0  # If no previous price, return 0
            
            return stocks_data, market_data, current_returns
            
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
            trade_len=self.args.trade_len,
            max_steps=self.args.max_steps,
            norm_type=self.args.norm_type,
            allow_short=True,
            mode='test'
        )
    
    def _create_agent(self, env: PortfolioEnv) -> RLAgent:
        return RLAgent(env, self.model, self.args)
    
    def process_end_of_day(self, event: EndOfDayEvent) -> None:
        """Process end of day event and save portfolio results"""
        try:
            # Get current date
            date = event.date.strftime("%Y-%m-%d")
            
            # Fetch data from MongoDB
            stocks_data, market_data, current_returns = self._fetch_data_from_mongodb(date)
            
            # Create environment with fetched data
            self.env = self._create_environment(stocks_data, market_data)
            
            # Create agent
            self.agent = self._create_agent(self.env)
            
            # Reset environment
            states, masks = self.env.reset()
            
            # Get model prediction
            with torch.no_grad():
                x_a = torch.from_numpy(states[0]).float().to(self.device)
                masks = torch.from_numpy(masks).bool().to(self.device)
                x_m = torch.from_numpy(states[1]).float().to(self.device)
                weights, rho, _, _ = self.model(x_a, x_m, masks, deterministic=True)
            
            # Convert weights to numpy
            if isinstance(weights, torch.Tensor):
                weights_np = weights[0].cpu().numpy()
            else:
                weights_np = weights[0]
            
            # Extract long and short positions
            num_assets = stocks_data.shape[0]
            long_weights = weights_np[:num_assets]
            short_weights = weights_np[num_assets:] if len(weights_np) > num_assets else np.zeros(num_assets)
            
            # Normalize long weights to ensure they sum to 1
            long_weights_sum = np.sum(long_weights)
            if long_weights_sum > 0:
                long_weights = long_weights / long_weights_sum
            else:
                long_weights = np.ones(num_assets) / num_assets
            
            # During inference, current returns should be 0 since we haven't made any trades yet
            current_returns = np.zeros(num_assets)
            
            # Calculate expected return based on model's prediction
            # The model's prediction includes future returns in its state
            future_returns = self.env.ror[0]  # Get the first future return from the environment
            
            # Calculate expected returns for both long and short positions
            long_expected_return = float(np.sum(long_weights * future_returns))
            short_expected_return = float(np.sum(short_weights * future_returns))
            
            # Total expected return is the sum of long and short returns
            expected_return = long_expected_return - short_expected_return  # Short returns are negative
            
            # Create portfolio result
            portfolio_result = PortfolioResult(
                tickers=TARGET_TICKERS,
                portfolio_weights=weights_np.tolist(),
                long_ratio=float(rho[0]),
                expected_return=expected_return,
                date_index=stocks_data.shape[1] - 1,
                returns=current_returns.tolist(),  # Current returns are 0 during inference
                date=event.date
            )
            
            # Save to MongoDB
            self.mongodb.insert_one(MONGODB_COLLECTION_PORTFOLIO, portfolio_result.to_dict())
            
        except Exception as e:
            print(f"Error processing end of day: {str(e)}")
            raise 