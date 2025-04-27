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
from common.config.db_config import MONGODB_COLLECTION_OHLC
from common.config.target_tickers import TARGET_TICKERS


def fetch_data_from_mongodb(target_tickers, start_date=None, end_date=None, limit_days=800):
    """
    Fetch stock and market data from MongoDB using ml_model_helper.
    
    Args:
        target_tickers: List of tickers to fetch data for
        start_date: Start date in 'YYYY-MM-DD' format
        end_date: End date for data collection (YYYY-MM-DD)
        limit_days: Number of days to limit the data to (for testing)
        
    Returns:
        tuple: (stocks_data, market_history)
            stocks_data: numpy array of shape (num_stocks, num_days, 5)
            market_history: numpy array of shape (num_days, 5)
    """
    helper = MlModelHelper()
    
    # Initialize data structures
    all_dates = set()
    stock_data_dict = {ticker: [] for ticker in target_tickers}
    
    # Print debug information
    print(f"Attempting to fetch data for {len(target_tickers)} tickers from MongoDB")
    print(f"Collection: {MONGODB_COLLECTION_OHLC}")
    
    # Fetch data for each ticker
    for ticker in target_tickers:
        query = {"ticker": ticker}
        if start_date:
            query["date"] = {"$gte": start_date}
        if end_date:
            query["date"] = {"$lte": end_date}
        
        # Print the query for debugging
        print(f"Query for {ticker}: {query}")
        
        # Check if the ticker exists in the collection
        # Use find().count() instead of count() method
        count = len(list(helper.mongodb.find(MONGODB_COLLECTION_OHLC, query)))
        print(f"Found {count} documents for {ticker}")
        
        if count == 0:
            print(f"Warning: No data found for ticker {ticker}")
            continue
            
        for doc in helper.mongodb.find(MONGODB_COLLECTION_OHLC, query):
            date = doc['date']
            all_dates.add(date)
            stock_data_dict[ticker].append({
                'date': date,
                'close': doc['close'],
                'high': doc['high'],
                'low': doc['low'],
                'volume': doc['volume'],
                'market_cap': doc.get('market_cap', doc['close'] * doc['volume'])
            })
    
    if not all_dates:
        print("ERROR: No data found for any of the tickers in MongoDB.")
        print("Available collections in MongoDB:")
        try:
            collections = helper.mongodb.list_collections()
            for collection in collections:
                print(f"  - {collection}")
        except Exception as e:
            print(f"Error listing collections: {e}")
        
        # Try to get a sample of available tickers
        print("\nChecking for available tickers in the collection:")
        try:
            # Use aggregation to get distinct tickers
            pipeline = [{"$group": {"_id": "$ticker"}}, {"$limit": 10}]
            sample_tickers = [doc["_id"] for doc in helper.mongodb.aggregate(MONGODB_COLLECTION_OHLC, pipeline)]
            if sample_tickers:
                print(f"Sample of available tickers: {sample_tickers}")
            else:
                print("No tickers found in the collection.")
        except Exception as e:
            print(f"Error getting sample tickers: {e}")
        
        # Create synthetic data for testing
        print("\nCreating synthetic data for testing...")
        num_stocks = len(target_tickers)
        num_days = 800
        stocks_data = np.random.randn(num_stocks, num_days, 5) * 0.1 + 1.0
        market_history = np.mean(stocks_data, axis=0)
        print(f"Created synthetic data with shape: {stocks_data.shape}")
        return stocks_data, market_history
    
    # Sort dates and create date index mapping
    all_dates = sorted(list(all_dates))
    print(f"Found data for {len(all_dates)} dates")
    
    # Limit the number of days for testing
    if limit_days and len(all_dates) > limit_days:
        all_dates = all_dates[-limit_days:]  # Take the most recent days
        print(f"Limited to {len(all_dates)} most recent days")
    
    date_to_idx = {date: idx for idx, date in enumerate(all_dates)}
    
    # Create numpy arrays
    num_stocks = len(target_tickers)
    num_days = len(all_dates)
    stocks_data = np.zeros((num_stocks, num_days, 5))
    market_history = np.zeros((num_days, 5))
    
    # Fill stock data
    for i, ticker in enumerate(target_tickers):
        for data_point in stock_data_dict[ticker]:
            if data_point['date'] in date_to_idx:
                idx = date_to_idx[data_point['date']]
                stocks_data[i, idx] = [
                    data_point['close'],
                    data_point['high'],
                    data_point['low'],
                    data_point['volume'],
                    data_point['market_cap']
                ]
    
    # Calculate market history (using mean of all stocks)
    market_history = np.mean(stocks_data, axis=0)
    
    print(f"Final data shape: {stocks_data.shape}")
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

    # Set up logging
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
        # Use a subset of tickers for testing
        test_tickers = TARGET_TICKERS[:10]  # Use only first 10 tickers for testing
        logger.info(f"Using {len(test_tickers)} tickers for testing")
        
        # Fetch data from MongoDB using test tickers
        stocks_data, market_history = fetch_data_from_mongodb(test_tickers, limit_days=800)
        
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
            synthetic_stocks_data = np.random.randn(func_args.num_assets, min_required_days, 5) * 0.1 + 1.0
            synthetic_market_history = np.mean(synthetic_stocks_data, axis=0)
            
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
        
        allow_short = True

        # Create environment
        env = PortfolioEnv(assets_data=stocks_data, market_data=market_history,
                           in_features=func_args.in_features, val_idx=test_idx, test_idx=test_idx,
                           batch_size=func_args.batch_size, window_len=func_args.window_len, trade_len=func_args.trade_len,
                           max_steps=func_args.max_steps, mode=func_args.mode, norm_type=func_args.norm_type,
                           allow_short=allow_short)

        # Create actor and agent
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
            epoch_pbar = tqdm(range(test_epochs), desc="Test Training Progress", position=0)
            for epoch in epoch_pbar:
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
                    print('New Best CR Policy!!!!')
                    max_cr = metrics['CR']
                    torch.save(actor, os.path.join(model_save_dir, 'best_cr-'+str(epoch)+'.pkl'))
                logger.warning('after training %d round, max wealth: %.4f, min wealth: %.4f,'
                               ' avg wealth: %.4f, final wealth: %.4f, ARR: %.3f%%, ASR: %.3f, AVol" %.3f,'
                               'MDD: %.2f%%, CR: %.3f, DDR: %.3f'
                               % (
                                   epoch, max(agent_wealth[0]), min(agent_wealth[0]), np.mean(agent_wealth),
                                   agent_wealth[-1, -1], 100 * metrics['APR'], metrics['ASR'], metrics['AVOL'],
                                   100 * metrics['MDD'], metrics['CR'], metrics['DDR']
                               ))
        except KeyboardInterrupt:
            torch.save(actor, os.path.join(model_save_dir, 'final_model.pkl'))
            torch.save(agent.optimizer.state_dict(), os.path.join(model_save_dir, 'final_optimizer.pkl'))
            logger.info("Training interrupted by user. Model saved.")
        
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