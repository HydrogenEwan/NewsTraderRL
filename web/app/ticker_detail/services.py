import requests
from pymongo import DESCENDING

from common.config.db_config import MONGODB_COLLECTION_PORTFOLIO, MONGODB_COLLECTION_NEWS
from common.config.financial_news_config import FINNHUB_API_KEY
from common.infrastructure.mongodb.mongodb_client import MongoDbClient
from common.model.financial_news import FinancialNews
from common.model.portfolio_result import PortfolioResult
from web.app.dto.ticker_detail_response import TickerDetailResponse, TickerWeight, CompanyProfile


def get_ticker_detail(ticker: str) -> TickerDetailResponse:
    mongodb = MongoDbClient.get_instance()

    lastdate = mongodb.get_latest_date(MONGODB_COLLECTION_PORTFOLIO)
    portfolio_doc = mongodb.find_one(MONGODB_COLLECTION_PORTFOLIO, {"date": lastdate})
    portfolio = PortfolioResult.from_raw(portfolio_doc)

    chart = []
    chart_docs = list(mongodb.find(MONGODB_COLLECTION_PORTFOLIO, {}, sort=[("date", DESCENDING)], limit=100))
    for chart_doc in chart_docs:
        item = PortfolioResult.from_raw(chart_doc)
        chart.append(TickerWeight(
            date=item.date.strftime("%Y-%m-%d"),
            weight=item.get_weight_by_ticker(ticker)
        ))

    news = []
    news_docs = list(mongodb.find(MONGODB_COLLECTION_NEWS, {"ticker": ticker}, sort=[("datetime", DESCENDING)], limit=10))
    for news_doc in news_docs:
        item = FinancialNews.from_raw(news_doc)
        if item:
            news.append(item)

    response = requests.get(f"https://finnhub.io/api/v1/stock/profile?symbol={ticker}&token={FINNHUB_API_KEY}", )
    company_profile = CompanyProfile.from_raw(response.json())

    return TickerDetailResponse(
        ticker=ticker,
        weight=portfolio.get_weight_by_ticker(ticker),
        returns=portfolio.get_return_by_ticker(ticker),
        sentiment=0.5,
        chart=chart,
        news = news,
        company_profile=company_profile
    )


if __name__ == "__main__":
    ticker = "AAPL"
    detail = get_ticker_detail(ticker)
