import argparse
import json
import os
import copy
import time
from datetime import datetime
import logging
from tqdm import *
import numpy as np
import torch
from torch.utils.tensorboard import SummaryWriter

from .utils.parse_config import ConfigParser
from .utils.functions import *
from .agent import *
from .environment.portfolio_env import PortfolioEnv
from ml_model.ml_model_helper import MlModelHelper
from common.config.db_config import MONGODB_COLLECTION_OHLC, MONGODB_COLLECTION_SENTIMENT, MONGODB_COLLECTION_SEC
from common.config.target_tickers import TARGET_TICKERS

import psutil
import gc

def fetch_data_from_mongodb(target_tickers, start_date=None, end_date=None):
    """
    Fetch stock and market data from MongoDB using ml_model_helper.
    
    Args:
        target_tickers: List of tickers to fetch data for
        start_date: Start date in 'YYYY-MM-DD' format
        end_date: End date in 'YYYY-MM-DD' format
        
    Returns:
        tuple: (stocks_data, market_history)
            stocks_data: numpy array of shape (num_stocks, num_days, 7)  # 7 features for stocks
            market_history: numpy array of shape (num_days, 5)  # 5 features for market
    """
    helper = MlModelHelper()
    logger = logging.getLogger()
    
    logger.info(f"Starting data fetch for {len(target_tickers)} tickers")
    if start_date:
        logger.info(f"Start date: {start_date}")
    if end_date:
        logger.info(f"End date: {end_date}")
    
    # Initialize data structures
    all_dates = set()
    stock_data_dict = {ticker: [] for ticker in target_tickers}
    
    # First, get all dates from OHLC data
    logger.info("Fetching OHLC data for all tickers...")
    for i, ticker in enumerate(target_tickers):
        logger.info(f"Processing ticker {i+1}/{len(target_tickers)}: {ticker}")
        try:
            query = {"ticker": ticker}
            if start_date:
                query["date"] = {"$gte": start_date}
            if end_date:
                query["date"] = {"$lte": end_date}
                
            doc_count = 0
            for doc in helper.mongodb.find(MONGODB_COLLECTION_OHLC, query):
                date = doc['date']
                all_dates.add(date)
                stock_data_dict[ticker].append({
                    'date': date,
                    'close': doc['close'],
                    'high': doc['high'],
                    'low': doc['low'],
                    'volume': doc['volume'],
                    'marketcap': doc.get('marketcap', 0.0),  # Default to 0.0 if not present
                    'sentiment': 0.0,  # Default sentiment score
                    'sec_score': 0.0   # Default SEC score
                })
                doc_count += 1
            
            logger.info(f"Found {doc_count} OHLC records for {ticker}")
        except Exception as e:
            logger.error(f"Error fetching OHLC data for {ticker}: {str(e)}")
            continue
    
    if not all_dates:
        raise ValueError(f"No data found for tickers {target_tickers} in MongoDB. Please check if the tickers exist and have data.")
    
    # Sort dates and create date index mapping
    all_dates = sorted(list(all_dates))
    date_to_idx = {date: idx for idx, date in enumerate(all_dates)}
    logger.info(f"Found {len(all_dates)} unique dates across all tickers")
    
    # Now get sentiment and SEC scores for all tickers and dates
    logger.info("Fetching sentiment and SEC scores...")
    
    # Create a mapping of ticker+date to sentiment and SEC scores
    sentiment_cache = {}
    sec_cache = {}
    
    # Batch process sentiment scores with direct MongoDB access for better performance
    logger.info("Batch processing sentiment scores...")
    for i, ticker in enumerate(target_tickers):
        logger.info(f"Processing sentiment for ticker {i+1}/{len(target_tickers)}: {ticker}")
        
        # Get all unique dates for this ticker
        ticker_dates = [data_point['date'] for data_point in stock_data_dict[ticker]]
        
        # Process in batches of 100 dates to reduce the number of database calls
        batch_size = 100
        for j in range(0, len(ticker_dates), batch_size):
            batch_dates = ticker_dates[j:j+batch_size]
            logger.info(f"  Processing batch {j//batch_size + 1}/{(len(ticker_dates) + batch_size - 1)//batch_size} ({len(batch_dates)} dates)")
            
            # Create a query to fetch sentiment for all dates in this batch
            query = {
                "ticker": ticker,
                "date": {"$in": batch_dates}
            }
            
            try:
                # Fetch all sentiment scores for this batch in one query
                sentiment_docs = list(helper.mongodb.find(MONGODB_COLLECTION_SENTIMENT, query))
                
                # Process the results
                for doc in sentiment_docs:
                    date = doc['date']
                    sentiment_cache[f"{ticker}_{date}"] = doc.get('avg_score', 0.0)
            except Exception as e:
                logger.warning(f"Error fetching sentiment batch for {ticker}: {str(e)}")
                # Continue with default values for this batch
    
    # Batch process SEC scores using the helper function
    logger.info("Batch processing SEC scores...")
    for i, ticker in enumerate(target_tickers):
        logger.info(f"Processing SEC scores for ticker {i+1}/{len(target_tickers)}: {ticker}")
        
        # Get all unique dates for this ticker
        ticker_dates = [data_point['date'] for data_point in stock_data_dict[ticker]]
        
        # Process in batches of 100 dates
        batch_size = 100
        for j in range(0, len(ticker_dates), batch_size):
            batch_dates = ticker_dates[j:j+batch_size]
            logger.info(f"  Processing batch {j//batch_size + 1}/{(len(ticker_dates) + batch_size - 1)//batch_size} ({len(batch_dates)} dates)")
            
            # Process each date in the batch using the helper function
            for date in batch_dates:
                try:
                    # Use the helper function to get SEC score
                    sec_score = helper.get_sec_score(ticker, date)
                    sec_cache[f"{ticker}_{date}"] = sec_score
                except Exception as e:
                    logger.warning(f"Error fetching SEC score for {ticker} on {date}: {str(e)}")
                    sec_cache[f"{ticker}_{date}"] = 0.0  # Default to neutral SEC score
    
    # Now update the stock data with sentiment and SEC scores from the cache
    logger.info("Updating stock data with sentiment and SEC scores...")
    for i, ticker in enumerate(target_tickers):
        for j, data_point in enumerate(stock_data_dict[ticker]):
            if j % 100 == 0 and j > 0:
                logger.info(f"  Processed {j}/{len(stock_data_dict[ticker])} dates for {ticker}")
                
            date = data_point['date']
            cache_key = f"{ticker}_{date}"
            
            # Get sentiment score from cache or use default
            data_point['sentiment'] = sentiment_cache.get(cache_key, 0.0)
            
            # Get SEC score from cache or use default
            data_point['sec_score'] = sec_cache.get(cache_key, 0.0)
    
    # Create numpy arrays
    num_stocks = len(target_tickers)
    num_days = len(all_dates)
    stocks_data = np.zeros((num_stocks, num_days, 7))  # 7 features for stocks
    logger.info(f"Creating stock data array with shape: {stocks_data.shape}")
    
    # Fill stock data
    for i, ticker in enumerate(target_tickers):
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
    
    # Fetch market data (S&P 100 index) from MongoDB
    logger.info("Fetching market data (S&P 100)...")
    market_data_dict = {}
    try:
        market_query = {"ticker": "^GSPC"}
        if start_date:
            market_query["date"] = {"$gte": start_date}
        if end_date:
            market_query["date"] = {"$lte": end_date}
        
        market_doc_count = 0
        for doc in helper.mongodb.find(MONGODB_COLLECTION_OHLC, market_query):
            date = doc['date']
            if date in date_to_idx:  # Only include dates that match our stock data
                market_data_dict[date] = {
                    'close': doc['close'],
                    'high': doc['high'],
                    'low': doc['low'],
                    'volume': doc['volume'],
                    'marketcap': doc.get('marketcap', 0.0)
                }
                market_doc_count += 1
        
        logger.info(f"Found {market_doc_count} market data records")
    except Exception as e:
        logger.error(f"Error fetching market data: {str(e)}")
    
    # Create market history array
    market_history = np.zeros((num_days, 5))  # 5 features for market
    logger.info(f"Creating market history array with shape: {market_history.shape}")
    
    # Fill market data
    missing_market_dates = 0
    for date, idx in date_to_idx.items():
        if date in market_data_dict:
            data = market_data_dict[date]
            market_history[idx] = [
                data['close'],
                data['high'],
                data['low'],
                data['volume'],
                data['marketcap']
            ]
        else:
            # If market data is missing for a date, use the mean of stock data for that day
            market_history[idx] = np.mean(stocks_data[:, idx, :5], axis=0)  # Only use the first 5 features
            missing_market_dates += 1
    
    if missing_market_dates > 0:
        logger.warning(f"Market data missing for {missing_market_dates} dates. Using mean of stock data instead.")
    
    logger.info("Data fetching complete!")
    return stocks_data, market_history


def run(func_args):
    if func_args.seed != -1:
        torch.manual_seed(func_args.seed)
        np.random.seed(func_args.seed)

    # Configure logging
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Create console handler with a higher log level
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # Create formatter and add it to the handler
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    
    # Add the handler to the logger
    logger.addHandler(console_handler)
    
    # Log the hyperparameters
    logger.info("Starting training with the following hyperparameters:")
    for key, value in func_args.__dict__.items():
        logger.info(f"  {key}: {value}")

    data_prefix = 'ml_model/rl_model/data/' + func_args.market + '/'
    matrix_path = data_prefix + func_args.relation_file

    start_time = datetime.now().strftime('%m%d_%H_%M_%S')
    if func_args.mode == 'train':
        PREFIX = 'outputs/'
        PREFIX = os.path.join(PREFIX, start_time)
        img_dir = os.path.join(PREFIX, 'img_file')
        save_dir = os.path.join(PREFIX, 'log_file')
        model_save_dir = os.path.join(PREFIX, 'model_file')

        if not os.path.isdir(save_dir):
            os.makedirs(save_dir)
        if not os.path.isdir(img_dir):
            os.makedirs(img_dir)
        if not os.path.isdir(model_save_dir):
            os.mkdir(model_save_dir)

        hyper = copy.deepcopy(func_args.__dict__)
        print(hyper)
        # Set device based on CUDA availability
        hyper['device'] = 'cuda' if torch.cuda.is_available() else 'cpu'
        logger.info(f"Using device: {hyper['device']}")
        json_str = json.dumps(hyper, indent=4)

        with open(os.path.join(save_dir, 'hyper.json'), 'w') as json_file:
            json_file.write(json_str)

        writer = SummaryWriter(save_dir)
        writer.add_text('hyper_setting', str(hyper))

        logger = logging.getLogger()
        logger.setLevel('INFO')
        BASIC_FORMAT = "%(asctime)s:%(levelname)s:%(message)s"
        DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
        formatter = logging.Formatter(BASIC_FORMAT, DATE_FORMAT)
        chlr = logging.StreamHandler()
        chlr.setFormatter(formatter)
        chlr.setLevel('WARNING')
        fhlr = logging.FileHandler(os.path.join(save_dir, 'logger.log'))
        fhlr.setFormatter(formatter)
        logger.addHandler(chlr)
        logger.addHandler(fhlr)

        try:
            # Use all tickers from TARGET_TICKERS
            logger.info(f"Using all {len(TARGET_TICKERS)} target tickers from config")
            
            # Fetch data from MongoDB using all tickers
            logger.info("Fetching data from MongoDB...")
            stocks_data, market_history = fetch_data_from_mongodb(TARGET_TICKERS)
            logger.info(f"Data fetch complete. Stocks data shape: {stocks_data.shape}, Market history shape: {market_history.shape}")
            
            # Debug: Print first few dates from stock data
            logger.info("First few dates from stock data:")
            for i in range(min(5, stocks_data.shape[1])):
                logger.info(f"Date {i}: Close prices: {stocks_data[0, i, 0]}")  # First stock's close price
            
            # Debug: Print first few dates from market data
            logger.info("\nFirst few dates from market data:")
            for i in range(min(5, market_history.shape[0])):
                logger.info(f"Date {i}: Close price: {market_history[i, 0]}")  # Market close price
            
            # Update num_assets in func_args to match the actual number of tickers
            func_args.num_assets = stocks_data.shape[0]
            logger.info(f"Updated num_assets to {func_args.num_assets} based on data shape")
            
            # Load and adjust the adjacency matrix if needed
            try:
                logger.info(f"Loading adjacency matrix from {matrix_path}")
                A = torch.from_numpy(np.load(matrix_path)).float()
                # Move to device after loading
                A = A.to(hyper['device'])
                # Check if the adjacency matrix dimensions match the number of tickers
                if A.shape[0] != func_args.num_assets or A.shape[1] != func_args.num_assets:
                    logger.warning(f"Adjacency matrix dimensions ({A.shape[0]}, {A.shape[1]}) don't match number of tickers ({func_args.num_assets})")
                    # Create a new identity matrix with the correct dimensions
                    A = torch.eye(func_args.num_assets, device=hyper['device'])
                    logger.info(f"Created new identity adjacency matrix with shape {A.shape}")
            except Exception as e:
                logger.warning(f"Error loading adjacency matrix: {e}. Creating identity matrix instead.")
                A = torch.eye(func_args.num_assets, device=hyper['device'])
            
            # Calculate test index dynamically based on data size and test ratio
            total_days = stocks_data.shape[1]
            test_ratio = getattr(func_args, 'test_ratio', 0.2)  # Default to 20% test set
            test_idx = int(total_days * (1 - test_ratio))
            logger.info(f"Total days: {total_days}, Test index: {test_idx} (using {test_ratio*100}% for testing)")

            def print_memory_usage(tag=""):
                process = psutil.Process()
                mem = process.memory_info().rss / 1024 / 1024  # in MB
                logger.info(f"[{tag}] Current RAM usage: {mem:.2f} MB")

            # After loading stocks_data and market_history
            logger.info("stocks_data shape: %s", stocks_data.shape)
            logger.info("market_history shape: %s", market_history.shape)
            logger.info("stocks_data size (MB): %.2f", stocks_data.nbytes / 1024 / 1024)
            logger.info("market_history size (MB): %.2f", market_history.nbytes / 1024 / 1024)
            print_memory_usage("After loading data")

            logger.info("CUDA available: %s", torch.cuda.is_available())
            logger.info("Current device: %s", hyper['device'])
            
            allow_short = True

            logger.info("Creating portfolio environment...")
            env = PortfolioEnv(assets_data=stocks_data, market_data=market_history,
                               in_features=func_args.in_features, val_idx=test_idx, test_idx=test_idx,
                               batch_size=func_args.batch_size, window_len=func_args.window_len, trade_len=func_args.trade_len,
                               max_steps=func_args.max_steps, mode=func_args.mode, norm_type=func_args.norm_type,
                               allow_short=allow_short)

            logger.info("Creating RL actor and agent...")
            supports = [A]
            actor = RLActor(supports, func_args).to(hyper['device'])
            agent = RLAgent(env, actor, func_args)

            mini_batch_num = int(np.ceil(len(env.src.order_set) / func_args.batch_size))
            if mini_batch_num == 0:
                raise ValueError("No data available for training. Please check if the data was loaded correctly.")
                
            try:
                max_cr = 0
                # Add outer progress bar for epochs

                print_memory_usage("Before training loop") #debugging code for GPU
                epoch_pbar = tqdm(range(func_args.epochs), desc="Training Progress", position=0)
                for epoch in epoch_pbar:
                    print_memory_usage(f"Start of epoch {epoch}") #debugging code for GPU
                    epoch_return = 0
                    # Update the description to show current epoch
                    epoch_pbar.set_description(f"Epoch {epoch+1}/{func_args.epochs}")
                    
                    for j in tqdm(range(mini_batch_num), desc=f"Mini-batches", position=1, leave=False):
                        episode_return, avg_rho, avg_mdd = agent.train_episode()
                        epoch_return += episode_return
                    avg_train_return = epoch_return / mini_batch_num
                    logger.warning('[%s]round %d, avg train return %.4f, avg rho %.4f, avg mdd %.4f' %
                                   (start_time, epoch, avg_train_return, avg_rho, avg_mdd))
                    agent_wealth = agent.evaluation()
                    metrics = calculate_metrics(agent_wealth, func_args.trade_mode)
                    writer.add_scalar('Test/APR', metrics['APR'], global_step=epoch)
                    writer.add_scalar('Test/MDD', metrics['MDD'], global_step=epoch)
                    writer.add_scalar('Test/AVOL', metrics['AVOL'], global_step=epoch)
                    writer.add_scalar('Test/ASR', metrics['ASR'], global_step=epoch)
                    writer.add_scalar('Test/SoR', metrics['DDR'], global_step=epoch)
                    writer.add_scalar('Test/CR', metrics['CR'], global_step=epoch)
                    
                    # Update the progress bar with metrics
                    epoch_pbar.set_postfix({
                        'CR': f"{float(metrics['CR']):.3f}",
                        'APR': f"{float(metrics['APR'])*100:.2f}%",
                        'MDD': f"{float(metrics['MDD'])*100:.2f}%"
                    })

                    if metrics['CR'] > max_cr:
                        logger.info('New Best CR Policy!!!!')
                        max_cr = metrics['CR']
                        torch.save(actor, os.path.join(model_save_dir, 'best_cr-'+str(epoch)+'.pkl'))

                    print_memory_usage(f"End of epoch {epoch}") #debugging code for GPU
                    logger.info(f"[run.py] Allocated: {torch.cuda.memory_allocated() / 1024**3:.2f} GB, Reserved: {torch.cuda.memory_reserved() / 1024**3:.2f} GB")
                    torch.cuda.empty_cache()
                    gc.collect()
                    
                    logger.warning('after training %d round, max wealth: %.4f, min wealth: %.4f,'
                                   ' avg wealth: %.4f, final wealth: %.4f, ARR: %.3f%%, ASR: %.3f, AVol" %.3f,'
                                   'MDD: %.2f%%, CR: %.3f, DDR: %.3f'
                                   % (
                                       epoch, max(agent_wealth[0]), min(agent_wealth[0]), np.mean(agent_wealth),
                                       agent_wealth[-1, -1], 100 * metrics['APR'], metrics['ASR'], metrics['AVOL'],
                                       100 * metrics['MDD'], metrics['CR'], metrics['DDR']
                                   ))
            except KeyboardInterrupt:
                logger.info("Training interrupted by user. Saving model...")
                torch.save(actor, os.path.join(model_save_dir, 'final_model.pkl'))
                torch.save(agent.optimizer.state_dict(), os.path.join(model_save_dir, 'final_optimizer.pkl'))
        except Exception as e:
            logger.error(f"Error during training: {str(e)}")
            raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', type=str)
    parser.add_argument('--window_len', type=int)
    parser.add_argument('--G', type=int)
    parser.add_argument('--batch_size', type=int)
    parser.add_argument('--seed', type=int, default=-1)
    parser.add_argument('--lr', type=float)
    parser.add_argument('--gamma', type=float)
    parser.add_argument('--no_spatial', dest='spatial_bool', action='store_false')
    parser.add_argument('--no_msu', dest='msu_bool', action='store_false')
    parser.add_argument('--relation_file', type=str)
    parser.add_argument('--addaptiveadj', dest='addaptive_adj_bool', action='store_false')
    parser.add_argument('--spatial_bool', type=bool, default=True)
    parser.add_argument('--msu_bool', type=bool, default=True)
    parser.add_argument('--addaptive_adj_bool', type=bool, default=True)
    parser.add_argument('--rho', type=float, default=0.1)

    opts = parser.parse_args()

    if opts.config is not None:
        with open(opts.config) as f:
            options = json.load(f)
            args = ConfigParser(options)
    else:
        with open('ml_model/rl_model/hyper.json') as f:
            options = json.load(f)
            args = ConfigParser(options)
    args.update(opts)

    run(args)
