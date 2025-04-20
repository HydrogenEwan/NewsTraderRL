# from common.config import db_config
# import finnhub
# from datetime import date, timedelta
# finnhub_client = finnhub.Client(api_key="d00hff9r01qk939o4ni0d00hff9r01qk939o4nig")
#
#
# def fetch_company_news(symbol: str):
#     today = date.today()
#     from_date = today - timedelta(days=1)
#     news = finnhub_client.company_news(symbol, _from=str(from_date), to=str(today))
#
#     for item in news:
#         item["ticker"] = symbol
#     return news
#
# if __name__ == '__main__':
#     print(db_config.MONGODB_COLLECTION_NEWS)
#
#     news = fetch_company_news("AAPL")
#     print(news)


from common.infrastructure.mongodb.mongodb_client import MongoDbClient
from common.config.db_config import MONGODB_COLLECTION_NEWS

def fetch_news_by_ticker(ticker: str):
    client = MongoDbClient()
    news_cursor = client.find(
        collection_name=MONGODB_COLLECTION_NEWS,
        filter={"ticker": ticker},
        sort=[("from_date", 1)]
    )
    return list(news_cursor)

if __name__ == '__main__':
    ticker = "AAPL"
    news_list = fetch_news_by_ticker(ticker)

    for news in news_list:
        print(f"- {news.get('headline', 'No headline')} | {news.get('datetime', 'No date')}")