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


# from common.infrastructure.mongodb.mongodb_client import MongoDbClient
# from common.config.db_config import MONGODB_COLLECTION_NEWS
#
# def fetch_news_by_ticker(ticker: str):
#     client = MongoDbClient()
#     news_cursor = client.find(
#         collection_name=MONGODB_COLLECTION_NEWS,
#         filter={"ticker": ticker},
#         sort=[("from_date", 1)]
#     )
#     return list(news_cursor)
#
# if __name__ == '__main__':
#     ticker = "AAPL"
#     news_list = fetch_news_by_ticker(ticker)
#
#     for news in news_list:
#         print(f"- {news.get('headline', 'No headline')} | {news.get('datetime', 'No date')}")

import pandas as pd
from datetime import datetime

# 파일 경로: constituents_changes.csv (https://github.com/fja05680/sp500/blob/main/data/constituents_changes.csv)
df = pd.read_csv('https://github.com/fja05680/sp500/blob/main/data/constituents_changes.csv')

# 날짜 문자열을 datetime으로 변환
df['date'] = pd.to_datetime(df['date'])

# 기준일: 2000-01-01
start_date = pd.to_datetime('2000-01-01')
today = pd.to_datetime(datetime.today().date())

# 2000-01-01 이전에 편입되고, 이후에 제거된 적 없는 종목
# 1. 2000-01-01 이전에 추가됨
added_before = df[(df['action'] == 'add') & (df['date'] <= start_date)]

# 2. 제거 기록이 없거나, 제거일이 start_date 이후
tickers = []
for symbol in added_before['ticker'].unique():
    removed = df[(df['ticker'] == symbol) & (df['action'] == 'remove')]
    if removed.empty or all(removed['date'] > today):
        tickers.append(symbol)

# 정렬해서 출력
tickers = sorted(tickers)
print(tickers)
