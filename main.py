import click

from common.config.target_tickers import TARGET_TICKERS
from data.ohlc.yahoo_ohlc_pipeline import YahooOhlcPipeline



@click.group()
def cli():
    """Main CLI Entry Point"""
    pass

# python3 main.py run-yahoo-pipeline --ticker AAPL,MSFT,GOOG --start 2024-01-01 --end 2024-03-31
@cli.command()
@click.option('--ticker', required=False ,help='Comma-separated ticker symbols (e.g. AAPL,MSFT)')
@click.option('--start', required=True, help='Start date (YYYY-MM-DD)')
@click.option('--end', required=True, help='End date (YYYY-MM-DD)')
@click.option('--issimulation', required=False, default=False)
def run_yahoo_pipeline(ticker, start, end, issimulation):
    pipeline = YahooOhlcPipeline()

    ticker_list = TARGET_TICKERS
    ticker_list.append("^GSPC")
    ticker_list.append("^VIX")
    if ticker is not None:
        ticker_list = [t.strip() for t in ticker.split(',') if t.strip()]

    for t in ticker_list:
        if issimulation:
            print(f"[INFO] Running simulation pipeline for {t}")
            pipeline.run_simulation_pipeline(ticker=t, start=start, end=end)
        else:
            print(f"[INFO] Running pipeline for {t}")
            pipeline.run_historical_pipeline(ticker=t, start=start, end=end)



if __name__ == '__main__':
    cli()
