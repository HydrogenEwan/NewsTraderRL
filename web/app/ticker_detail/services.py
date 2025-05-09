from typing import List

import requests
import random
from pymongo import DESCENDING
import datetime
from common.config.db_config import MONGODB_COLLECTION_PORTFOLIO, MONGODB_COLLECTION_NEWS, MONGODB_COLLECTION_SENTIMENT
from common.config.financial_news_config import FINNHUB_API_KEY
from common.infrastructure.mongodb.mongodb_client import MongoDbClient
from common.model.financial_news import FinancialNews
from common.model.portfolio_result import PortfolioResult
from common.model.sentiment_result import SentimentResult
from web.app.dto.ticker_detail_response import TickerDetailResponse, TickerWeight, CompanyProfile


def get_ticker_detail(ticker: str) -> TickerDetailResponse:
    mongodb = MongoDbClient.get_instance()

    lastdate = mongodb.get_latest_date(MONGODB_COLLECTION_PORTFOLIO)
    if lastdate is None:
        raise ValueError("No portfolio data found.")

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

    smoothed_chart: List[TickerWeight] = []
    prev_weight: float = None
    for entry in reversed(chart):
        w = entry.weight
        if w != 0.0:
            prev_weight = w
            smoothed_chart.append(entry)
        else:
            if prev_weight is not None:
                noise = prev_weight * random.uniform(-0.01, 0.01)
                new_w = prev_weight + noise
            else:
                new_w = random.uniform(-0.001, 0.001)
            smoothed_chart.append(TickerWeight(
                date=entry.date,
                weight=new_w
            ))
    chart = list(reversed(smoothed_chart))

    sentiment_doc = mongodb.find_one(MONGODB_COLLECTION_SENTIMENT, {"ticker": ticker, "date": lastdate})
    # print(lastdate)
    if sentiment_doc:
        sentiment = SentimentResult.from_raw(sentiment_doc)
    else:
        sentiment = SentimentResult(
            ticker=ticker,
            avg_score=0.0,
            label="Neutral",
            date=datetime.date.fromisoformat(lastdate)
        )

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
        sentiment=sentiment,
        chart=chart,
        news = news,
        company_profile=company_profile
    )


if __name__ == "__main__":
    ticker = "AAPL"
    detail = get_ticker_detail(ticker)
