from common.config.db_config import MONGODB_COLLECTION_PORTFOLIO
from common.infrastructure.mongodb.mongodb_client import MongoDbClient
from common.model.portfolio_result import PortfolioResult


def get_portfolio(date=None):
    mongodb = MongoDbClient()
    if date is None:
        date = mongodb.get_latest_date(MONGODB_COLLECTION_PORTFOLIO)

    portfolio_doc = mongodb.find_one(MONGODB_COLLECTION_PORTFOLIO, {"date": date})
    portfolio = PortfolioResult.from_raw(portfolio_doc)

    return portfolio