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
            stocks_data: numpy array of shape (num_stocks, num_days, 5)
            market_history: numpy array of shape (num_days, 5)
    """
    helper = MlModelHelper()
    
    # Initialize data structures
    all_dates = set()
    stock_data_dict = {ticker: [] for ticker in target_tickers}
    
    # Fetch data for each ticker
    for ticker in target_tickers:
        query = {"ticker": ticker}
        if start_date:
            query["date"] = {"$gte": start_date}
        if end_date:
            query["date"] = {"$lte": end_date}
            
        for doc in helper.mongodb.find(MONGODB_COLLECTION_OHLC, query):
            date = doc['date']
            all_dates.add(date)
            stock_data_dict[ticker].append({
                'date': date,
                'close': doc['close'],
                'high': doc['high'],
                'low': doc['low'],
                'volume': doc['volume'],
                'marketcap': doc.get('marketcap')
            })
    
    if not all_dates:
        raise ValueError(f"No data found for tickers {target_tickers} in MongoDB. Please check if the tickers exist and have data.")
    
    # Sort dates and create date index mapping
    all_dates = sorted(list(all_dates))
    date_to_idx = {date: idx for idx, date in enumerate(all_dates)}
    
    # Create numpy arrays
    num_stocks = len(target_tickers)
    num_days = len(all_dates)
    stocks_data = np.zeros((num_stocks, num_days, 5))
    
    # Fill stock data
    for i, ticker in enumerate(target_tickers):
        for data_point in stock_data_dict[ticker]:
            idx = date_to_idx[data_point['date']]
            stocks_data[i, idx] = [
                data_point['close'],
                data_point['high'],
                data_point['low'],
                data_point['volume'],
                data_point['marketcap']
            ]
    
    # Fetch market data (S&P 500 index) from MongoDB
    market_data_dict = {}
    market_query = {"ticker": "^GSPC"}
    if start_date:
        market_query["date"] = {"$gte": start_date}
    if end_date:
        market_query["date"] = {"$lte": end_date}
    
    for doc in helper.mongodb.find(MONGODB_COLLECTION_OHLC, market_query):
        date = doc['date']
        if date in date_to_idx:  # Only include dates that match our stock data
            market_data_dict[date] = {
                'close': doc['close'],
                'high': doc['high'],
                'low': doc['low'],
                'volume': doc['volume'],
                'marketcap': doc.get('marketcap')
            }
    
    # Create market history array
    market_history = np.zeros((num_days, 5))
    
    # Fill market data
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
            market_history[idx] = np.mean(stocks_data[:, idx], axis=0)
            logger = logging.getLogger()
            logger.warning(f"Market data missing for date {date}. Using mean of stock data instead.")
    
    return stocks_data, market_history


def run(func_args):
    if func_args.seed != -1:
        torch.manual_seed(func_args.seed)
        np.random.seed(func_args.seed)

    data_prefix = 'ml_model/model1/data/' + func_args.market + '/'
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
        hyper['device'] = 'cuda' if hyper['device'] == torch.device('cuda') else 'cpu'
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
            stocks_data, market_history = fetch_data_from_mongodb(TARGET_TICKERS)
            
            # Update num_assets in func_args to match the actual number of tickers
            func_args.num_assets = stocks_data.shape[0]
            logger.info(f"Updated num_assets to {func_args.num_assets} based on data shape")
            
            # Load and adjust the adjacency matrix if needed
            try:
                A = torch.from_numpy(np.load(matrix_path)).float().to(func_args.device)
                # Check if the adjacency matrix dimensions match the number of tickers
                if A.shape[0] != func_args.num_assets or A.shape[1] != func_args.num_assets:
                    logger.warning(f"Adjacency matrix dimensions ({A.shape[0]}, {A.shape[1]}) don't match number of tickers ({func_args.num_assets})")
                    # Create a new identity matrix with the correct dimensions
                    A = torch.eye(func_args.num_assets, device=func_args.device)
                    logger.info(f"Created new identity adjacency matrix with shape {A.shape}")
            except Exception as e:
                logger.warning(f"Error loading adjacency matrix: {e}. Creating identity matrix instead.")
                A = torch.eye(func_args.num_assets, device=func_args.device)
            
            # Calculate test index dynamically based on data size and test ratio
            total_days = stocks_data.shape[1]
            test_ratio = getattr(func_args, 'test_ratio', 0.2)  # Default to 20% test set
            test_idx = int(total_days * (1 - test_ratio))
            logger.info(f"Total days: {total_days}, Test index: {test_idx} (using {test_ratio*100}% for testing)")

            def print_memory_usage(tag=""):
                process = psutil.Process()
                mem = process.memory_info().rss / 1024 / 1024  # in MB
                print(f"[{tag}] Current RAM usage: {mem:.2f} MB")

            # After loading stocks_data and market_history
            print("stocks_data shape:", stocks_data.shape)
            print("market_history shape:", market_history.shape)
            print("stocks_data size (MB):", stocks_data.nbytes / 1024 / 1024)
            print("market_history size (MB):", market_history.nbytes / 1024 / 1024)
            print_memory_usage("After loading data")

            print("CUDA available:", torch.cuda.is_available())
            print("Current device:", torch.cuda.current_device())
            print("Device count:", torch.cuda.device_count())
            print("Device name:", torch.cuda.get_device_name(0))
            
            allow_short = True

            env = PortfolioEnv(assets_data=stocks_data, market_data=market_history,
                               in_features=func_args.in_features, val_idx=test_idx, test_idx=test_idx,
                               batch_size=func_args.batch_size, window_len=func_args.window_len, trade_len=func_args.trade_len,
                               max_steps=func_args.max_steps, mode=func_args.mode, norm_type=func_args.norm_type,
                               allow_short=allow_short)

            supports = [A]
            actor = RLActor(supports, func_args).to(func_args.device)
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
                        print('New Best CR Policy!!!!')
                        max_cr = metrics['CR']
                        torch.save(actor, os.path.join(model_save_dir, 'best_cr-'+str(epoch)+'.pkl'))

                    print_memory_usage(f"End of epoch {epoch}") #debugging code for GPU
                    print(f"[run.py] Allocated: {torch.cuda.memory_allocated() / 1024**3:.2f} GB, Reserved: {torch.cuda.memory_reserved() / 1024**3:.2f} GB")
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
        with open('ml_model/model1/hyper.json') as f:
            options = json.load(f)
            args = ConfigParser(options)
    args.update(opts)

    run(args)
