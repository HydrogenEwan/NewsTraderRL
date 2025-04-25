import os
import sys
import json
import torch
import numpy as np
from datetime import datetime, timedelta

# Add the src directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent import RLActor, RLAgent
from environment.portfolio_env import PortfolioEnv

def test_model(model_path, data_dir, dates):
    """
    Test the model for specific dates and return results.
    
    Args:
        model_path: Path to the saved model
        data_dir: Directory containing the data files
        dates: List of dates to test
        
    Returns:
        Dictionary containing results for each date
    """
    try:
        # Load data
        print("Loading data...")
        stocks_data = np.load(os.path.join(data_dir, 'stocks_data.npy'))
        ror_data = np.load(os.path.join(data_dir, 'ror.npy'))
        market_data = np.load(os.path.join(data_dir, 'market_data.npy'))
        industry_matrix = np.load(os.path.join(data_dir, 'industry_classification.npy'))
        
        # Get ticker information based on the data directory
        market = os.path.basename(data_dir)  # e.g., 'DJIA', 'HSI', 'CSI100', 'SP500'
        if market == 'DJIA':
            tickers = [
                'AAPL', 'AMGN', 'AXP', 'BA', 'CAT', 'CRM', 'CSCO', 'CVX', 'DIS', 'DOW',
                'GS', 'HD', 'HON', 'IBM', 'INTC', 'JNJ', 'JPM', 'KO', 'MCD', 'MMM',
                'MRK', 'MSFT', 'NKE', 'PG', 'TRV', 'UNH', 'V', 'VZ', 'WBA', 'WMT'
            ]
        elif market == 'HSI':
            tickers = [
                '0700.HK', '0941.HK', '0001.HK', '0005.HK', '0011.HK',
                '0027.HK', '0066.HK', '0386.HK', '0388.HK', '0883.HK'
            ]
        elif market == 'CSI100':
            tickers = [
                '600519.SS', '000858.SZ', '601318.SS', '600036.SS', '601166.SS',
                '600276.SS', '601328.SS', '601288.SS', '601398.SS', '601988.SS'
            ]
        elif market == 'SP500':
            # For S&P 500, we'll use the actual components from the data
            # The tickers will be loaded from the industry classification matrix
            tickers = [f"Stock_{i}" for i in range(stocks_data.shape[0])]
        else:
            tickers = [f"Stock_{i}" for i in range(stocks_data.shape[0])]
        
        print(f"Data loaded. Shape: stocks={stocks_data.shape}, ror={ror_data.shape}")
        print(f"Tickers: {tickers}")
        
        # Set up device
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        print(f"Using device: {device}")
        
        # Add RLActor to safe globals
        torch.serialization.add_safe_globals(['agent.RLActor'])
        
        # Load model
        print(f"Loading model from {model_path}")
        model = torch.load(model_path, map_location=device, weights_only=False)
        
        # Create args object
        class Args:
            def __init__(self):
                self.lr = 1e-4
                self.weight_decay = 1e-5
                self.max_grad_norm = 1.0
                self.eta = 0.01
                self.rho = 0.1
                self.device = device
                self.G = 5
                self.msu_bool = True
                self.spatial_bool = True
                self.addaptiveadj = True
                self.in_features = [5, 5]
                self.hidden_dim = 128
                self.window_len = 13
                self.dropout = 0.1
                self.kernel_size = 2
                self.num_blocks = 4
                self.num_assets = stocks_data.shape[0]
        
        args = Args()
        
        # Create environment
        print("Creating environment...")
        env = PortfolioEnv(
            assets_data=stocks_data,
            market_data=market_data,
            rtns_data=ror_data,
            in_features=args.in_features,
            val_idx=int(stocks_data.shape[1] * 0.8),
            test_idx=int(stocks_data.shape[1] * 0.8),
            batch_size=1,
            window_len=args.window_len,
            trade_len=21,
            max_steps=12,
            norm_type='div-last',
            allow_short=True,
            mode='test'
        )
        
        # Create agent
        agent = RLAgent(env, model, args)
        
        results = {}
        total_days = stocks_data.shape[1]
        print(f"Total days in dataset: {total_days}")
        
        for date in dates:
            try:
                print(f"\nProcessing date: {date}")
                # Calculate date index - use middle of the dataset for testing
                date_idx = total_days // 2
                print(f"Using date index: {date_idx}")
                
                # Reset environment
                env.src.cursor = np.array([date_idx])
                states, masks = env.reset()
                
                # Get model prediction
                with torch.no_grad():
                    x_a = torch.from_numpy(states[0]).float().to(device)
                    masks = torch.from_numpy(masks).bool().to(device)
                    x_m = torch.from_numpy(states[1]).float().to(device)
                    weights, rho, _, _ = model(x_a, x_m, masks, deterministic=True)
                
                # Convert weights to numpy
                if isinstance(weights, torch.Tensor):
                    weights_np = weights[0].cpu().numpy()
                else:
                    weights_np = weights[0]
                
                # Extract long positions and ensure they sum to 1
                num_assets = stocks_data.shape[0]
                long_weights = weights_np[:num_assets]
                
                # Normalize weights to ensure they sum to 1
                long_weights_sum = np.sum(long_weights)
                if long_weights_sum > 0:
                    long_weights = long_weights / long_weights_sum
                else:
                    print("Warning: Long weights sum to zero, using equal weights")
                    long_weights = np.ones(num_assets) / num_assets
                
                # Get returns for the current date
                current_returns = ror_data[:, date_idx]
                
                # Handle NaN or infinite values in returns
                current_returns = np.nan_to_num(current_returns, nan=0.0, posinf=0.0, neginf=0.0)
                
                # Calculate expected return with safety checks
                expected_return = float(np.sum(long_weights * current_returns))
                
                # If expected return is NaN, set it to 0
                if np.isnan(expected_return):
                    print("Warning: Expected return is NaN, setting to 0")
                    expected_return = 0.0
                
                
                # Store results
                results[date] = {
                    'portfolio_weights': weights_np.tolist(),
                    'long_weights': long_weights.tolist(),
                    'short_weights': weights_np[num_assets:].tolist(),
                    'long_ratio': float(rho[0]),
                    'expected_return': expected_return,
                    'date_index': date_idx,
                    'returns': current_returns.tolist(),
                    'tickers': tickers,
                }
                print(f"Successfully processed {date}")
                print(f"Expected return: {expected_return}")
                
            except Exception as e:
                error_msg = f"Error processing date {date}: {str(e)}"
                print(error_msg)
                results[date] = {
                    'error': error_msg,
                    'traceback': str(e.__traceback__)
                }
        
        return results
        
    except Exception as e:
        error_msg = f"Fatal error in test_model: {str(e)}"
        print(error_msg)
        return {date: {'error': error_msg} for date in dates}

def main():
    # Set parameters
    model_path = 'outputs/0420/23:45:00/model_file/best_cr-10.pkl'
    data_dir = 'data/DJIA'
    
    # Test dates
    test_dates = ['2023-04-20', '2023-04-21', '2023-04-22']
    
    # Run test
    try:
        print("Starting model testing...")
        results = test_model(model_path, data_dir, test_dates)
        
        # Save results
        output_dir = 'outputs/test_results'
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, 'test_results.json')
        
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=4)
        
        print(f"\nResults saved to {output_file}")
        
    except Exception as e:
        print(f"Error during testing: {e}")
        print(f"Traceback: {e.__traceback__}")

if __name__ == "__main__":
    main()
