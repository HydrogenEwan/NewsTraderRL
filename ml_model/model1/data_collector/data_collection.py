import numpy as np
import yfinance as yf
import pandas as pd
import logging
from datetime import datetime, timedelta
import os
import json

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataCollector:
    def __init__(self, market='SP500', start_date=None, end_date=None):
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
        
        # Market-specific configurations
        self.market_configs = {
            'DJIA': {
                'index_symbol': '^DJI',
                'components': self._get_djia_components()
            },
            'HSI': {
                'index_symbol': '^HSI',
                'components': self._get_hsi_components()
            },
            'CSI100': {
                'index_symbol': '000300.SS',
                'components': self._get_csi100_components()
            },
            'SP500': {
                'index_symbol': '^GSPC',
                'components': self._get_sp500_components()
            }
        }
        
        # Create data directory if it doesn't exist
        self.data_dir = os.path.join('data', market)
        os.makedirs(self.data_dir, exist_ok=True)

    def _get_djia_components(self):
        """Get DJIA component stocks."""
        # This is a static list as of 2024
        return [
            'AAPL', 'AMGN', 'AXP', 'BA', 'CAT', 'CRM', 'CSCO', 'CVX', 'DIS', 'DOW',
            'GS', 'HD', 'HON', 'IBM', 'INTC', 'JNJ', 'JPM', 'KO', 'MCD', 'MMM',
            'MRK', 'MSFT', 'NKE', 'PG', 'TRV', 'UNH', 'V', 'VZ', 'WBA', 'WMT'
        ]

    def _get_hsi_components(self):
        """Get HSI component stocks."""
        # This would need to be updated regularly
        # For now, returning a subset of major HSI components
        return [
            '0700.HK', '0941.HK', '0001.HK', '0005.HK', '0011.HK',
            '0027.HK', '0066.HK', '0386.HK', '0388.HK', '0883.HK'
        ]

    def _get_csi100_components(self):
        """Get CSI100 component stocks."""
        # This would need to be updated regularly
        # For now, returning a subset of major CSI100 components
        return [
            '600519.SS', '000858.SZ', '601318.SS', '600036.SS', '601166.SS',
            '600276.SS', '601328.SS', '601288.SS', '601398.SS', '601988.SS'
        ]

    def _get_sp500_components(self):
        """Get S&P 500 component stocks."""
        try:
            # Note: This requires the lxml package to be installed
            # Install it using: pip install lxml
            table = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')
            df = table[0]
            # Extract ticker symbols and remove any dots
            tickers = [ticker.replace('.', '-') for ticker in df['Symbol'].tolist()]
            logger.info(f"Successfully retrieved {len(tickers)} S&P 500 components")
            return tickers
        except Exception as e:
            logger.error(f"Error retrieving S&P 500 components: {e}")
            # Return a subset of major S&P 500 components as fallback
            return [
                'AAPL', 'MSFT', 'AMZN', 'GOOGL', 'META', 'NVDA', 'BRK-B', 'JPM', 'JNJ', 'V',
                'PG', 'MA', 'HD', 'CVX', 'AVGO', 'ABBV', 'LLY', 'PFE', 'BAC', 'KO',
                'PEP', 'TMO', 'COST', 'DHR', 'CSCO', 'MRK', 'ABT', 'VZ', 'CRM', 'ACN'
            ]

    def collect_stock_data(self):
        """
        Collect daily stock data for all components.
        Returns:
            numpy.ndarray: Stock data with shape (num_stocks, num_days, 5)
            Each stock has 5 features: [Close, High, Low, Volume, Market Cap]
            
        Note: For stocks that don't have data for certain time periods (e.g., 
        companies that weren't in the S&P 500 at that time), the data will be set to 0.
        """
        logger.info(f"Collecting stock data for {self.market} components...")
        components = self.market_configs[self.market]['components']
        stock_data = []
        valid_components = []
        
        # Check for existing progress file
        progress_file = os.path.join(self.data_dir, 'collection_progress.json')
        if os.path.exists(progress_file):
            try:
                with open(progress_file, 'r') as f:
                    progress = json.load(f)
                    completed_symbols = progress.get('completed_symbols', [])
                    logger.info(f"Found progress file with {len(completed_symbols)} completed symbols")
                    # Filter out already completed symbols
                    components = [sym for sym in components if sym not in completed_symbols]
            except Exception as e:
                logger.warning(f"Error reading progress file: {e}")
        
        # First, determine the date range for all data
        all_dates = None
        for symbol in components:
            try:
                stock = yf.Ticker(symbol)
                data = stock.history(start=self.start_date, end=self.end_date)
                if len(data) > 0:
                    if all_dates is None:
                        all_dates = data.index
                    else:
                        # Update all_dates to include all unique dates
                        all_dates = all_dates.union(data.index)
            except Exception as e:
                logger.warning(f"Error checking data range for {symbol}: {e}")
        
        if all_dates is None:
            logger.error("No data available for any components")
            return None
        
        # Sort dates to ensure consistent ordering
        all_dates = sorted(all_dates)
        logger.info(f"Data collection period: {all_dates[0]} to {all_dates[-1]}, {len(all_dates)} days")
        
        # Now collect data for each component, filling in zeros for missing dates
        from tqdm import tqdm
        import time
        
        for i, symbol in enumerate(tqdm(components, desc="Collecting stock data")):
            try:
                # Add rate limiting to avoid API throttling
                if i > 0 and i % 10 == 0:  # Pause every 10 requests
                    time.sleep(1)  # 1 second pause
                    
                stock = yf.Ticker(symbol)
                data = stock.history(start=self.start_date, end=self.end_date)
                
                if len(data) > 0:
                    # Create a DataFrame with all dates, filling missing values with 0
                    full_data = pd.DataFrame(index=all_dates)
                    full_data['Close'] = data['Close'].reindex(all_dates, fill_value=0)
                    full_data['High'] = data['High'].reindex(all_dates, fill_value=0)
                    full_data['Low'] = data['Low'].reindex(all_dates, fill_value=0)
                    full_data['Volume'] = data['Volume'].reindex(all_dates, fill_value=0)
                    # Calculate MarketCap using fillna instead of fill_value
                    full_data['MarketCap'] = (full_data['Close'] * full_data['Volume']).fillna(0)
                    
                    # Extract required features
                    features = np.array([
                        full_data['Close'].values,
                        full_data['High'].values,
                        full_data['Low'].values,
                        full_data['Volume'].values,
                        full_data['MarketCap'].values
                    ]).T
                    
                    stock_data.append(features)
                    valid_components.append(symbol)
                    logger.info(f"Successfully collected data for {symbol}")
                else:
                    # Create zero-filled data for components with no data
                    features = np.zeros((len(all_dates), 5))
                    stock_data.append(features)
                    valid_components.append(symbol)
                    logger.warning(f"No data available for {symbol}, using zeros")
                    
                # Update progress file after each successful collection
                try:
                    with open(progress_file, 'r') as f:
                        progress = json.load(f)
                except (FileNotFoundError, json.JSONDecodeError):
                    progress = {'completed_symbols': []}
                    
                progress['completed_symbols'].append(symbol)
                with open(progress_file, 'w') as f:
                    json.dump(progress, f, indent=4)
                    
            except Exception as e:
                logger.error(f"Error collecting data for {symbol}: {e}")
                # Create zero-filled data for components with errors
                features = np.zeros((len(all_dates), 5))
                stock_data.append(features)
                valid_components.append(symbol)
        
        # Convert to numpy array
        final_data = np.array(stock_data)
        
        # Save component list for reference in text format
        with open(os.path.join(self.data_dir, 'components.txt'), 'w') as f:
            f.write('\n'.join(valid_components))
        
        # Save component list in JSON format
        components_data = {
            'market': self.market,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'num_components': len(valid_components),
            'components': valid_components
        }
        with open(os.path.join(self.data_dir, 'components.json'), 'w') as f:
            json.dump(components_data, f, indent=4)
        
        # Save to file
        np.save(os.path.join(self.data_dir, 'stocks_data.npy'), final_data)
        logger.info(f"Stock data saved with shape {final_data.shape}")
        
        # Clean up progress file after successful completion
        if os.path.exists(progress_file):
            os.remove(progress_file)
        
        return final_data

    def collect_market_data(self):
        """
        Collect market index data.
        Returns:
            numpy.ndarray: Market data with shape (num_days, 5)
            Features: [Close, High, Low, Volume, Market Cap]
        """
        logger.info(f"Collecting market data for {self.market}...")
        index_symbol = self.market_configs[self.market]['index_symbol']
        
        try:
            market = yf.Ticker(index_symbol)
            data = market.history(start=self.start_date, end=self.end_date)
            
            if len(data) > 0:
                features = np.array([
                    data['Close'].values,
                    data['High'].values,
                    data['Low'].values,
                    data['Volume'].values,
                    (data['Close'] * data['Volume']).values
                ]).T
                
                # Save to file
                np.save(os.path.join(self.data_dir, 'market_data.npy'), features)
                logger.info(f"Market data saved with shape {features.shape}")
                return features
            else:
                logger.error(f"No market data available for {index_symbol}")
                return None
        except Exception as e:
            logger.error(f"Error collecting market data: {e}")
            return None

    def calculate_returns(self, stock_data):
        """
        Calculate daily returns from stock data.
        Args:
            stock_data (numpy.ndarray): Stock data array
        Returns:
            numpy.ndarray: Rate of return data
        
        Note: For stocks with zero values (indicating they weren't in the index at that time),
        the returns will be set to 0.
        """
        logger.info("Calculating daily returns...")
        returns = np.zeros_like(stock_data[:, :, 0])
        
        for i in range(stock_data.shape[0]):
            prices = stock_data[i, :, 0]  # Close prices
            
            # Handle zero prices (indicating the stock wasn't in the index at that time)
            # For the first day, set return to 0
            returns[i, 0] = 0
            
            # For subsequent days, calculate returns only if both current and previous prices are non-zero
            for j in range(1, prices.shape[0]):
                if prices[j] > 0 and prices[j-1] > 0:
                    returns[i, j] = (prices[j] - prices[j-1]) / prices[j-1]
                else:
                    # If either price is zero, set return to 0
                    returns[i, j] = 0
        
        # Save to file
        np.save(os.path.join(self.data_dir, 'ror.npy'), returns)
        logger.info(f"Returns data saved with shape {returns.shape}")
        return returns


    def collect_all_data(self):
        """
        Collect all necessary data for the model.
        """
        logger.info(f"Starting data collection for {self.market}...")
        
        # Collect stock data
        stock_data = self.collect_stock_data()
        
        # Collect market data
        market_data = self.collect_market_data()
        
        # Calculate returns
        returns = self.calculate_returns(stock_data)
        

        
        logger.info("Data collection completed successfully!")
        return {
            'stock_data': stock_data,
            'market_data': market_data,
            'returns': returns
        }

if __name__ == '__main__':
    # Example usage
    collector = DataCollector(market='SP500')
    data = collector.collect_all_data()