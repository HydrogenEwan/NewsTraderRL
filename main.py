import click

from common.config.target_tickers import TARGET_TICKERS
from data.ohlc.yahoo_ohlc_pipeline import YahooOhlcPipeline
# from web.app.initialize import create_app


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
    if ticker is not None:
        ticker_list = [t.strip() for t in ticker.split(',') if t.strip()]

    for t in ticker_list:
        if issimulation:
            print(f"[INFO] Running simulation pipeline for {t}")
            pipeline.run_simulation_pipeline(ticker=t, start=start, end=end)
        else:
            print(f"[INFO] Running pipeline for {t}")
            pipeline.run_historical_pipeline(ticker=t, start=start, end=end)


# @cli.command()
# @click.option('--host', default='0.0.0.0', help='Host to run the web server on')
# @click.option('--port', default=5000, help='Port to run the web server on')
# @click.option('--debug', is_flag=True, help='Run Flask in debug mode')
# def run_web(host, port, debug):
#     app = create_app()
#     app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    cli()
