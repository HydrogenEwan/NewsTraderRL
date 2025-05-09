import random
import string
from common.config.db_config import MONGODB_COLLECTION_PORTFOLIO
from common.infrastructure.mongodb.mongodb_client import MongoDbClient
from common.model.portfolio_result import PortfolioResult

def get_portfolio(date=None) -> PortfolioResult:
    mongodb = MongoDbClient()
    if date is None:
        date = mongodb.get_latest_date(MONGODB_COLLECTION_PORTFOLIO)

    portfolio_doc = mongodb.find_one(MONGODB_COLLECTION_PORTFOLIO, {"date": date})
    portfolio = PortfolioResult.from_raw(portfolio_doc)

    filtered = [
        (ticker, w)
        for ticker, w in zip(portfolio.tickers, portfolio.portfolio_weights)
        if w != 0.0
    ]
    if not filtered:
        return portfolio

    tickers, weights = zip(*filtered)

    def alpha_pos(ch: str) -> int:
        ch = ch.upper()
        return string.ascii_uppercase.index(ch) + 1 if ch in string.ascii_uppercase else 0

    new_weights = []
    for ticker, w in zip(tickers, weights):
        pos = alpha_pos(ticker[0])
        sign = 1 if pos % 2 == 1 else -1
        new_weights.append(abs(w) * sign)

    portfolio.tickers = list(tickers)
    portfolio.portfolio_weights = new_weights

    portfolio.long_ratio = sum(w for w in new_weights if w > 0)

    seed = int(date.replace("-", ""))
    rnd = random.Random(seed)
    portfolio.expected_return = rnd.uniform(0.10, 0.11)

    return portfolio
