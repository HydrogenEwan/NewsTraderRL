import click
from datetime import datetime, timedelta

from common.config.db_config import MONGODB_COLLECTION_SIMULATION_OHLC, MONGODB_COLLECTION_OHLC
from common.config.financial_news_config import FINNHUB_API_KEY
from common.config.target_tickers import TARGET_TICKERS
from data.financial_news.financial_api_news_pipeline import FinancialApiNewsPipeline
from data.ohlc.yahoo_ohlc_pipeline import YahooOhlcPipeline
from ml_model.ml_model_helper import MlModelHelper


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
def run_simulation(ticker, start, end, issimulation):
    ticker_list = TARGET_TICKERS
    ticker_list.append("^GSPC")
    ticker_list.append("^VIX")
    if ticker is not None:
        ticker_list = [t.strip() for t in ticker.split(',') if t.strip()]

    pipeline = YahooOhlcPipeline()
    for t in ticker_list:
        print(f"[INFO] Running simulation for MarketData {t}")
        pipeline.run_pipeline(ticker=t, start=start, end=end, collection=MONGODB_COLLECTION_OHLC)

    pipeline = FinancialApiNewsPipeline(FINNHUB_API_KEY)
    for t in ticker_list:
        print(f"[INFO] Running real-time pipeline for News {t}")
        pipeline.run(t, start, end)

    helper = MlModelHelper()
    start_date = datetime.strptime(start, "%Y-%m-%d").date()
    end_date = datetime.strptime(end, "%Y-%m-%d").date()
    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime("%Y-%m-%d")
        print(f"[INFO] Sending end-of-day stream event to models for {date_str}")
        helper.send_end_of_day_to_sentiment(date_str)
        current_date += timedelta(days=1)

@cli.command()
@click.option('--ticker', required=False ,help='Comma-separated ticker symbols (e.g. AAPL,MSFT)')
@click.option('--start', required=True, help='Start date (YYYY-MM-DD)')
@click.option('--end', required=True, help='End date (YYYY-MM-DD)')
@click.option('--issimulation', required=False, default=False)
def run_realtime(ticker, start, end, issimulation):
    ticker_list = TARGET_TICKERS
    ticker_list.append("^GSPC")
    ticker_list.append("^VIX")
    if ticker is not None:
        ticker_list = [t.strip() for t in ticker.split(',') if t.strip()]

    pipeline = YahooOhlcPipeline()
    for t in ticker_list:
        print(f"[INFO] Running real-time pipeline for MarketData {t}")
        pipeline.run_pipeline(ticker=t, start=start, end=end, collection=MONGODB_COLLECTION_OHLC)

    pipeline = FinancialApiNewsPipeline(FINNHUB_API_KEY)
    for t in ticker_list:
        print(f"[INFO] Running real-time pipeline for News {t}")
        pipeline.run(t, start, end)



@cli.command()
def run_sentiment():
    from ml_model.sentiment_helper import SAHelper
    sentiment = SAHelper()
    sentiment.listen_end_of_day_for_sentiment(sentiment.eod_callback)


@cli.command()
def run_rl():
    from ml_model.rl_model.rl_model_handler import RLModelHandler
    model_path = "ml_model/rl_model/trained_model_file/model_7dim_top20_output/model_file/best_cr-34.pth"  # Path to the trained model
    rl_handler = RLModelHandler(model_path)

    ml_helper = MlModelHelper()
    ml_helper.listen_end_of_day_for_rl(rl_handler.process_end_of_day)


if __name__ == '__main__':
    cli()
