import numpy as np
import yfinance as yf
import pandas as pd
import logging
from datetime import datetime, timedelta
import os
import json
import time
from tqdm import tqdm
import argparse
from common.config.target_tickers import TARGET_TICKERS

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MatrixMaker:
    def __init__(self, market='SP100', start_date=None, end_date=None):
        """
        Initialize the data collector.
        
        Args:
            market (str): Market index to collect data for ('DJIA', 'HSI', 'CSI100', 'SP500')
            start_date (str): Start date for data collection (YYYY-MM-DD)
            end_date (str): End date for data collection (YYYY-MM-DD)
        """
        self.market = market
        self.start_date = start_date or '1999-01-01'  # Default to January 1, 1999
        self.end_date = end_date or datetime.now().strftime('%Y-%m-%d')
        
        # Create data directory if it doesn't exist
        self.data_dir = os.path.join('ml_model/model1/data', market)
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Use TARGET_TICKERS from common/config/target_tickers.py
        self.components = TARGET_TICKERS[:10]
        logger.info(f"Using {len(self.components)} tickers from common/config/target_tickers.py")
        
        # Market-specific configurations
        self.market_configs = {
            'SP500': {
                'index_symbol': '^GSPC',
                'components': self.components
            }
        }
         
    def collect_industry_info(self):
        """
        Collect industry and sector information for all components.
        Returns:
            dict: Dictionary mapping ticker symbols to their industry and sector information
        """
        logger.info("Collecting industry information for all components...")
        components = self.market_configs[self.market]['components']
        industry_info = {}
        
        # Check for existing industry info file
        industry_info_file = os.path.join(self.data_dir, 'industry_info.json')
        if os.path.exists(industry_info_file):
            try:
                with open(industry_info_file, 'r') as f:
                    industry_info = json.load(f)
                    logger.info(f"Loaded industry information for {len(industry_info)} stocks")
                    return industry_info
            except Exception as e:
                logger.warning(f"Error loading industry info from {industry_info_file}: {e}")
        
        # Rate limiting parameters
        base_delay = 2  # Base delay in seconds
        max_delay = 60  # Maximum delay in seconds
        rate_limit_count = 0  # Count of rate limit errors
        
        # Collect industry information for each stock
        for i, symbol in enumerate(tqdm(components, desc="Collecting industry info")):
            # Add rate limiting to avoid API throttling
            if i > 0 and i % 5 == 0:  # Pause every 5 requests
                # Calculate delay with exponential backoff
                delay = min(base_delay * (2 ** rate_limit_count), max_delay)
                logger.info(f"Pausing for {delay} seconds to avoid rate limiting...")
                time.sleep(delay)
            
            try:
                stock = yf.Ticker(symbol)
                info = stock.info
                
                # Extract relevant information
                industry_info[symbol] = {
                    'industry': info.get('industry', 'Unknown'),
                    'sector': info.get('sector', 'Unknown')
                }
                
                # Reset rate limit count on success
                rate_limit_count = 0
                
            except Exception as e:
                error_msg = str(e)
                logger.warning(f"Error collecting info for {symbol}: {error_msg}")
                
                # Check if it's a rate limit error
                if "Too Many Requests" in error_msg or "rate limit" in error_msg.lower():
                    rate_limit_count += 1
                    delay = min(base_delay * (2 ** rate_limit_count), max_delay)
                    logger.warning(f"Rate limit detected. Pausing for {delay} seconds...")
                    time.sleep(delay)
                
                # Set default values
                industry_info[symbol] = {
                    'industry': 'Unknown',
                    'sector': 'Unknown'
                }
            
            # Save progress every 20 stocks
            if (i + 1) % 20 == 0:
                with open(industry_info_file, 'w') as f:
                    json.dump(industry_info, f, indent=4)
        
        # Save final industry information
        with open(industry_info_file, 'w') as f:
            json.dump(industry_info, f, indent=4)
        
        logger.info(f"Industry information collected for {len(industry_info)} stocks")
        return industry_info

    def create_industry_classification(self, num_stocks, industry_info=None):
        """
        Create industry classification matrix based on industry information.
        Args:
            num_stocks (int): Number of stocks
            industry_info (dict, optional): Pre-collected industry information
        Returns:
            numpy.ndarray: Industry classification matrix
        """
        logger.info("Creating industry classification matrix...")
        components = self.market_configs[self.market]['components']
        
        # Create industry-based matrix
        industry_matrix = np.zeros((num_stocks, num_stocks))
        
        # If industry_info is not provided, collect it
        if industry_info is None:
            industry_info = self.collect_industry_info()
        
        # Group stocks by industry
        industry_groups = {}
        for symbol in components:
            info = industry_info.get(symbol, {'industry': 'Unknown', 'sector': 'Unknown'})
            industry = info['industry']
            if industry not in industry_groups:
                industry_groups[industry] = []
            industry_groups[industry].append(symbol)
        
        # Create the classification matrix
        for i, symbol1 in enumerate(tqdm(components, desc="Creating matrix")):
            info1 = industry_info.get(symbol1, {'industry': 'Unknown', 'sector': 'Unknown'})
            industry1 = info1['industry']
            
            # Handle unknown industry case
            if industry1 == 'Unknown':
                industry_matrix[i, i] = 1.0  # Set diagonal to 1 for unknown industries
                continue
            
            # Get all stocks in the same industry
            same_industry_stocks = industry_groups.get(industry1, [])
            
            # Calculate the weight for each stock in the same industry
            if len(same_industry_stocks) > 1:
                weight = 1.0 / len(same_industry_stocks)
            else:
                weight = 1.0
            
            # Set the weights in the matrix
            for symbol2 in same_industry_stocks:
                j = components.index(symbol2)
                industry_matrix[i, j] = weight
        
        # Save to file
        np.save(os.path.join(self.data_dir, 'industry_classification_test.npy'), industry_matrix)
        logger.info(f"Industry classification matrix saved with shape {industry_matrix.shape}")
        
        return industry_matrix
    

if __name__ == '__main__':
    # Example usage
    import time
    from tqdm import tqdm
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Create industry classification matrix')
    parser.add_argument('--market', type=str, default='SP500', help='Market to process (default: SP500)')
    parser.add_argument('--batch-size', type=int, default=0, help='Process in batches of this size (0 for all at once)')
    parser.add_argument('--skip-collection', action='store_true', help='Skip collecting industry info and use existing file')
    args = parser.parse_args()
    
    collector = MatrixMaker(market=args.market)
    num_stocks = len(collector.market_configs[collector.market]['components'])
    print(f"Creating industry classification matrix for {num_stocks} stocks...")
    
    # Add progress tracking
    start_time = time.time()
    
    # Step 1: Collect industry information
    industry_info = None
    if not args.skip_collection:
        print("\nStep 1: Collecting industry information...")
        industry_info = collector.collect_industry_info()
        print(f"Industry information saved to: {os.path.join(collector.data_dir, 'industry_info.json')}")
    else:
        print("\nSkipping industry information collection, using existing file...")
        industry_info_file = os.path.join(collector.data_dir, 'industry_info.json')
        if os.path.exists(industry_info_file):
            with open(industry_info_file, 'r') as f:
                industry_info = json.load(f)
                print(f"Loaded industry information for {len(industry_info)} stocks")
        else:
            print("Warning: Industry info file not found. Will collect information now.")
    
    # Step 2: Create the matrix
    print("\nStep 2: Creating industry classification matrix...")
    if args.batch_size > 0:
        # Process in batches
        print(f"Processing in batches of {args.batch_size} stocks...")
        batch_size = min(args.batch_size, num_stocks)
        num_batches = (num_stocks + batch_size - 1) // batch_size
        
        for batch in range(num_batches):
            start_idx = batch * batch_size
            end_idx = min((batch + 1) * batch_size, num_stocks)
            print(f"\nProcessing batch {batch+1}/{num_batches} (stocks {start_idx+1}-{end_idx})...")
            
            # Create a temporary collector with only the stocks in this batch
            batch_components = collector.components[start_idx:end_idx]
            batch_collector = MatrixMaker(market=args.market)
            batch_collector.components = batch_components
            batch_collector.market_configs[args.market]['components'] = batch_components
            
            # Filter industry info for this batch
            batch_industry_info = {symbol: industry_info.get(symbol, {'industry': 'Unknown', 'sector': 'Unknown'}) 
                                  for symbol in batch_components}
            
            # Process this batch
            batch_matrix = batch_collector.create_industry_classification(len(batch_components), batch_industry_info)
            
            # Save the batch matrix
            batch_file = os.path.join(collector.data_dir, f'industry_classification_batch_{batch+1}.npy')
            np.save(batch_file, batch_matrix)
            print(f"Batch {batch+1} matrix saved to: {batch_file}")
            
            # Pause between batches to avoid rate limiting
            if batch < num_batches - 1:
                pause_time = 10  # 10 seconds between batches
                print(f"Pausing for {pause_time} seconds before next batch...")
                time.sleep(pause_time)
        
        # Combine batch matrices
        print("\nCombining batch matrices...")
        combined_matrix = np.zeros((num_stocks, num_stocks))
        
        for batch in range(num_batches):
            batch_file = os.path.join(collector.data_dir, f'industry_classification_batch_{batch+1}.npy')
            batch_matrix = np.load(batch_file)
            
            start_idx = batch * batch_size
            end_idx = min((batch + 1) * batch_size, num_stocks)
            batch_size_actual = end_idx - start_idx
            
            # Place the batch matrix in the correct position in the combined matrix
            combined_matrix[start_idx:end_idx, start_idx:end_idx] = batch_matrix
            
            # Remove the batch file
            os.remove(batch_file)
        
        # Save the combined matrix
        np.save(os.path.join(collector.data_dir, 'industry_classification.npy'), combined_matrix)
        industry_matrix = combined_matrix
    else:
        # Process all at once
        industry_matrix = collector.create_industry_classification(num_stocks, industry_info)
    
    end_time = time.time()
    
    print(f"Industry classification matrix created in {end_time - start_time:.2f} seconds")
    print(f"Matrix shape: {industry_matrix.shape}")
    print(f"Matrix saved to: {os.path.join(collector.data_dir, 'industry_classificationt.npy')}")