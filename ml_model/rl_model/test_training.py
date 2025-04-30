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


def fetch_data_from_mongodb(target_tickers, start_date=None, end_date=None, limit_days=800):
    """
    Fetch stock and market data from MongoDB using ml_model_helper.
    
    Args:
        target_tickers: List of tickers to fetch data for
        start_date: Start date in 'YYYY-MM-DD' format
        end_date: End date in 'YYYY-MM-DD' format
        limit_days: Number of days to limit the data to (for testing)
        
    Returns:
        tuple: (stocks_data, market_history)
            stocks_data: numpy array of shape (num_stocks, num_days, 7)  # 7 features for stocks
            market_history: numpy array of shape (num_days, 5)  # 5 features for market
    """
    target_tickers = TARGET_TICKERS[:10]
    helper = MlModelHelper()
    logger = logging.getLogger()
    
    logger.info(f"Starting data fetch for {len(target_tickers)} tickers")
    if start_date:
        logger.info(f"Start date: {start_date}")
    if end_date:
        logger.info(f"End date: {end_date}")
    if limit_days:
        logger.info(f"Limiting data to {limit_days} days")
    
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
                
            # Add sort and limit to get only the most recent data
            if limit_days:
                # First, get the total count of documents
                count = 0
                for _ in helper.mongodb.find(MONGODB_COLLECTION_OHLC, query):
                    count += 1
                
                # If we have more documents than limit_days, only fetch the most recent ones
                if count > limit_days:
                    # Sort by date in descending order and limit to limit_days
                    cursor = helper.mongodb.find(MONGODB_COLLECTION_OHLC, query).sort("date", -1).limit(limit_days)
                    # Convert to list and reverse to get chronological order
                    docs = list(cursor)
                    docs.reverse()
                else:
                    # If we have fewer documents than limit_days, fetch all of them
                    docs = list(helper.mongodb.find(MONGODB_COLLECTION_OHLC, query))
            else:
                # If no limit_days specified, fetch all documents
                docs = list(helper.mongodb.find(MONGODB_COLLECTION_OHLC, query))
                
            doc_count = 0
            for doc in docs:
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
    
    # Batch process sentiment scores with larger batch sizes
    logger.info("Batch processing sentiment scores...")
    for i, ticker in enumerate(target_tickers):
        logger.info(f"Processing sentiment for ticker {i+1}/{len(target_tickers)}: {ticker}")
        
        # Get all unique dates for this ticker
        ticker_dates = [data_point['date'] for data_point in stock_data_dict[ticker]]
        
        # Process in larger batches to reduce the number of database calls
        batch_size = 100  # Increased from 50 to 100
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
                    # Use get() with a default value to avoid KeyError
                    sentiment_cache[f"{ticker}_{date}"] = doc.get('avg_score', 0.0)
            except Exception as e:
                logger.warning(f"Error fetching sentiment batch for {ticker}: {str(e)}")
                # Continue with default values for this batch
    
    # Batch process SEC scores with larger batch sizes
    logger.info("Batch processing SEC scores...")
    for i, ticker in enumerate(target_tickers):
        logger.info(f"Processing SEC scores for ticker {i+1}/{len(target_tickers)}: {ticker}")
        
        # Get all unique dates for this ticker
        ticker_dates = [data_point['date'] for data_point in stock_data_dict[ticker]]
        
        # Process in larger batches
        batch_size = 100  # Increased from 50 to 100
        for j in range(0, len(ticker_dates), batch_size):
            batch_dates = ticker_dates[j:j+batch_size]
            logger.info(f"  Processing batch {j//batch_size + 1}/{(len(ticker_dates) + batch_size - 1)//batch_size} ({len(batch_dates)} dates)")
            
            # Create a query to fetch SEC scores for all dates in this batch
            query = {
                "ticker": ticker,
                "date": {"$in": batch_dates}
            }
            
            try:
                # Fetch all SEC scores for this batch in one query
                sec_docs = list(helper.mongodb.find(MONGODB_COLLECTION_SEC, query))
                
                # Process the results
                for doc in sec_docs:
                    date = doc['date']
                    # Use get() with a default value to avoid KeyError
                    sec_cache[f"{ticker}_{date}"] = doc.get('score', 0.0)
            except Exception as e:
                logger.warning(f"Error fetching SEC batch for {ticker}: {str(e)}")
                # Continue with default values for this batch
    
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
        
        # Apply the same limit_days logic to market data
        if limit_days:
            # First, get the total count of documents
            count = 0
            for _ in helper.mongodb.find(MONGODB_COLLECTION_OHLC, market_query):
                count += 1
            
            # If we have more documents than limit_days, only fetch the most recent ones
            if count > limit_days:
                # Sort by date in descending order and limit to limit_days
                cursor = helper.mongodb.find(MONGODB_COLLECTION_OHLC, market_query).sort("date", -1).limit(limit_days)
                # Convert to list and reverse to get chronological order
                market_docs = list(cursor)
                market_docs.reverse()
            else:
                # If we have fewer documents than limit_days, fetch all of them
                market_docs = list(helper.mongodb.find(MONGODB_COLLECTION_OHLC, market_query))
        else:
            # If no limit_days specified, fetch all documents
            market_docs = list(helper.mongodb.find(MONGODB_COLLECTION_OHLC, market_query))
        
        market_doc_count = 0
        for doc in market_docs:
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


def test_training(func_args):
    """
    Test the training process with a smaller dataset and fewer epochs.
    
    Args:
        func_args: Configuration arguments
    """
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
    logger.info("Starting test training with the following hyperparameters:")
    for key, value in func_args.__dict__.items():
        logger.info(f"  {key}: {value}")

    # Create a test directory for outputs
    start_time = datetime.now().strftime('%m%d_%H_%M_%S')
    PREFIX = 'outputs/test_' + start_time
    img_dir = os.path.join(PREFIX, 'img_file')
    save_dir = os.path.join(PREFIX, 'log_file')
    model_save_dir = os.path.join(PREFIX, 'model_file')

    if not os.path.isdir(save_dir):
        os.makedirs(save_dir)
    if not os.path.isdir(img_dir):
        os.makedirs(img_dir)
    if not os.path.isdir(model_save_dir):
        os.mkdir(model_save_dir)

    # Save hyperparameters
    hyper = copy.deepcopy(func_args.__dict__)
    print(hyper)
    hyper['device'] = 'cuda' if hyper['device'] == torch.device('cuda') else 'cpu'
    json_str = json.dumps(hyper, indent=4)

    with open(os.path.join(save_dir, 'hyper.json'), 'w') as json_file:
        json_file.write(json_str)

    writer = SummaryWriter(save_dir)
    writer.add_text('hyper_setting', str(hyper))

    # Add file handler for logging to file
    file_handler = logging.FileHandler(os.path.join(save_dir, 'logger.log'))
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    try:
        # Use a subset of tickers for testing
        test_tickers = TARGET_TICKERS[:10]  # Use only first 10 tickers for testing
        logger.info(f"Using {len(test_tickers)} tickers for testing")
        
        # Fetch data from MongoDB using test tickers
        logger.info("Fetching data from MongoDB...")
        stocks_data, market_history = fetch_data_from_mongodb(test_tickers, limit_days=800)  # Limit to 800 days for testing
        logger.info(f"Data fetch complete. Stocks data shape: {stocks_data.shape}, Market history shape: {market_history.shape}")
        
        # Update num_assets in func_args to match the actual number of tickers
        func_args.num_assets = stocks_data.shape[0]
        logger.info(f"Updated num_assets to {func_args.num_assets} based on data shape")
        
        # Calculate the minimum required days based on window_len and trade_len
        total_days = stocks_data.shape[1]
        logger.info(f"Total days in data: {total_days}")
        
        # Calculate minimum required days for the environment
        min_required_days = (func_args.window_len + 1) * 5 + func_args.trade_len + 1
        logger.info(f"Minimum required days: {min_required_days}")
        
        # Check if we have enough data
        if total_days < min_required_days:
            logger.warning(f"Not enough data ({total_days} days) for the required window_len ({func_args.window_len}) and trade_len ({func_args.trade_len})")
            logger.warning(f"Creating synthetic data with {min_required_days} days")
            
            # Create synthetic data with enough days
            synthetic_stocks_data = np.random.randn(func_args.num_assets, min_required_days, 7) * 0.1 + 1.0
            synthetic_market_history = np.mean(synthetic_stocks_data[:, :, :5], axis=0)
            
            # Replace the real data with synthetic data
            stocks_data = synthetic_stocks_data
            market_history = synthetic_market_history
            total_days = min_required_days
            
            logger.info(f"Created synthetic data with shape: {stocks_data.shape}")
        else:
            # Adjust window_len and trade_len to match the available data
            max_window_len = (total_days - 1) // 5 - 1  # Each window_len requires 5 days, and we need extra for trade_len
            max_trade_len = total_days - (max_window_len * 5) - 1
            
            # Adjust window_len and trade_len if they're too large
            if func_args.window_len > max_window_len:
                logger.warning(f"window_len {func_args.window_len} is too large for the available data. Adjusting to {max_window_len}")
                func_args.window_len = max_window_len
            
            if func_args.trade_len > max_trade_len:
                logger.warning(f"trade_len {func_args.trade_len} is too large for the available data. Adjusting to {max_trade_len}")
                func_args.trade_len = max_trade_len
            
            logger.info(f"Using window_len: {func_args.window_len}, trade_len: {func_args.trade_len}")
        
        # Load and adjust the adjacency matrix if needed
        matrix_path = os.path.join('ml_model/model1/data', func_args.market, func_args.relation_file)
        try:
            logger.info(f"Loading adjacency matrix from {matrix_path}")
            A = torch.from_numpy(np.load(matrix_path)).float().to(func_args.device)
            # Check if the adjacency matrix dimensions match the number of tickers
            if A.shape[0] != func_args.num_assets or A.shape[1] != func_args.num_assets:
                logger.warning(f"Adjacency matrix dimensions ({A.shape[0]}, {A.shape[1]}) don't match number of tickers ({func_args.num_assets})")
                # Create a new identity matrix with the correct dimensions
                A = torch.eye(func_args.num_assets, device=func_args.device)
                logger.info(f"Created new identity adjacency matrix with shape {A.shape}")
                
                # Save the new adjacency matrix for future use
                new_matrix_path = os.path.join('ml_model/model1/data', func_args.market, 'test_identity_matrix.npy')
                os.makedirs(os.path.dirname(new_matrix_path), exist_ok=True)
                np.save(new_matrix_path, A.cpu().numpy())
                logger.info(f"Saved new identity matrix to {new_matrix_path}")
        except Exception as e:
            logger.warning(f"Error loading adjacency matrix: {e}. Creating identity matrix instead.")
            A = torch.eye(func_args.num_assets, device=func_args.device)
            
            # Save the new adjacency matrix for future use
            new_matrix_path = os.path.join('ml_model/model1/data', func_args.market, 'test_identity_matrix.npy')
            os.makedirs(os.path.dirname(new_matrix_path), exist_ok=True)
            np.save(new_matrix_path, A.cpu().numpy())
            logger.info(f"Saved new identity matrix to {new_matrix_path}")
        
        # Calculate test index dynamically based on data size and test ratio
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
        logger.info("Current device: %s", torch.cuda.current_device())
        logger.info("Device count: %s", torch.cuda.device_count())
        logger.info("Device name: %s", torch.cuda.get_device_name(0))
        
        allow_short = True

        # Create environment
        logger.info("Creating portfolio environment...")
        env = PortfolioEnv(assets_data=stocks_data, market_data=market_history,
                           in_features=func_args.in_features, val_idx=test_idx, test_idx=test_idx,
                           batch_size=func_args.batch_size, window_len=func_args.window_len, trade_len=func_args.trade_len,
                           max_steps=func_args.max_steps, mode=func_args.mode, norm_type=func_args.norm_type,
                           allow_short=allow_short)

        # Create actor and agent
        logger.info("Creating RL actor and agent...")
        supports = [A]
        actor = RLActor(supports, func_args).to(func_args.device)
        agent = RLAgent(env, actor, func_args)

        # Calculate mini-batch number
        mini_batch_num = int(np.ceil(len(env.src.order_set) / func_args.batch_size))
        if mini_batch_num == 0:
            logger.warning("No data available for training. Creating synthetic data for testing...")
            # Create synthetic data for testing
            env.src.order_set = list(range(10))  # Create 10 synthetic orders
            mini_batch_num = 1
            logger.info(f"Created {len(env.src.order_set)} synthetic orders for testing")
        
        # Test training with fewer epochs
        test_epochs = min(3, func_args.epochs)  # Use at most 3 epochs for testing
        logger.info(f"Testing training with {test_epochs} epochs (original: {func_args.epochs})")
        
        try:
            max_cr = 0
            # Add outer progress bar for epochs
            print_memory_usage("Before training loop") #debugging code for GPU
            epoch_pbar = tqdm(range(test_epochs), desc="Test Training Progress", position=0)
            for epoch in epoch_pbar:
                print_memory_usage(f"Start of epoch {epoch}") #debugging code for GPU
                epoch_return = 0
                # Update the description to show current epoch
                epoch_pbar.set_description(f"Test Epoch {epoch+1}/{test_epochs}")
                
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
                logger.info(f"[test_training.py] Allocated: {torch.cuda.memory_allocated() / 1024**3:.2f} GB, Reserved: {torch.cuda.memory_reserved() / 1024**3:.2f} GB")
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
        
        logger.info("Test training completed successfully!")
        logger.info(f"Test outputs saved to: {PREFIX}")
        
    except Exception as e:
        logger.error(f"Error during test training: {str(e)}")
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
        with open('ml_model/model1/hyper.json') as f:
            options = json.load(f)
            args = ConfigParser(options)
    args.update(opts)

    test_training(args) 