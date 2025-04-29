from __future__ import annotations
import unittest
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Union

from common.config.db_config import MONGODB_COLLECTION_PORTFOLIO
from common.infrastructure.mongodb.mongodb_client import MongoDbClient
from common.model.daily_basis_model import DailyBasisModel


@dataclass
class PortfolioResult(DailyBasisModel):
    tickers: List[str]
    portfolio_weights: List[float]
    long_ratio: float
    expected_return: float
    date_index: int
    returns: List[float]
    error: Optional[str] = None
    traceback: Optional[str] = None

    @staticmethod
    def from_raw(doc: dict) -> PortfolioResult:
        # parse date field
        dt = doc["date"]
        if isinstance(dt, str):
            dt = datetime.date.fromisoformat(dt)

        return PortfolioResult(
            tickers=list(doc["tickers"]),
            portfolio_weights=[float(w) for w in doc["portfolio_weights"]],
            long_ratio=float(doc["long_ratio"]),
            expected_return=float(doc["expected_return"]),
            date_index=int(doc["date_index"]),
            returns=[float(r) for r in doc["returns"]],
            error=doc.get("error"),
            traceback=doc.get("traceback"),
            date=dt
        )

    def to_dict(self) -> dict:
        return {
            "date": self.date.strftime("%Y-%m-%d"),
            "tickers": self.tickers,
            "portfolio_weights": self.portfolio_weights,
            "long_ratio": self.long_ratio,
            "expected_return": self.expected_return,
            "date_index": self.date_index,
            "returns": self.returns,
            "error": self.error,
            "traceback": self.traceback
        }


class PortfolioResults:
    def __init__(self):
        self.results: Dict[str, PortfolioResult] = {}

    def add_portfolio_result(self, date: str, result: PortfolioResult):
        self.results[date] = result

    def to_dict(self) -> Dict[str, dict]:
        return {
            date: result.__dict__ for date, result in self.results.items()
        }


# Test class for PortfolioResults
# class TestPortfolioResults(unittest.TestCase):
#     def test_to_dict(self):
#         results = PortfolioResults()
#
#         results.add_portfolio_result("2023-04-20", PortfolioResult(
#             tickers=["AAPL", "AMD"],
#             portfolio_weights=[0.3, -0.2],
#             long_ratio=0.5,
#             expected_return=0.0012,
#             date_index=123,
#             returns=[0.02, -0.01]
#         ))
#
#         results.add_portfolio_result("2023-04-21", PortfolioResult(
#             tickers=[],
#             portfolio_weights=[],
#             long_ratio=0.0,
#             expected_return=0.0,
#             date_index=124,
#             returns=[],
#             error="Error processing date 2023-04-21",
#             traceback="Fake traceback object"
#         ))
#
#         output = results.to_dict()
#
#         self.assertIn("2023-04-20", output)
#         self.assertIn("2023-04-21", output)
#         self.assertEqual(output["2023-04-20"]["tickers"], ["AAPL", "AMD"])
#         self.assertEqual(output["2023-04-21"]["error"], "Error processing date 2023-04-21")
#         self.assertEqual(output["2023-04-21"]["traceback"], "Fake traceback object")
#
#         import json
#         print(json.dumps(output, indent=2))

if __name__ == '__main__':
    # unittest.main()
    import datetime
    from dataclasses import dataclass, field
    from typing import List, Optional

    import numpy as np
    import pandas as pd
    import yfinance as yf
    from common.config.target_tickers import TARGET_TICKERS

    top10 = ['AAPL', 'MSFT', 'NVDA', 'AMZN', 'GOOG', 'GOOGL', 'META', 'BRK-B', 'TSLA', 'AVGO']
    dates = pd.date_range(start="2016-01-01", end="2025-04-27", freq="B")

    n = len(top10)
    prev_weights = np.random.rand(n)
    prev_weights /= np.abs(prev_weights).sum()

    prev_returns = np.zeros(n)

    results: List[dict] = []

    for idx, dt in enumerate(dates):
        w = prev_weights * 0.9 + np.random.normal(scale=0.01, size=n)
        w /= np.abs(w).sum()
        prev_weights = w

        r = prev_returns * 0.9 + np.random.normal(scale=0.005, size=n)
        prev_returns = r

        long_ratio = float(np.sum(w[w > 0]))
        expected_return = float(np.dot(w, r))

        pr = PortfolioResult(
            tickers=top10,
            portfolio_weights=w.tolist(),
            long_ratio=long_ratio,
            expected_return=expected_return,
            date_index=idx,
            returns=r.tolist(),
            date=dt.strftime("%Y-%m-%d")
        )

        results.append(pr.to_dict())

    print(results)
    mongodb = MongoDbClient()
    mongodb.insert_many(MONGODB_COLLECTION_PORTFOLIO, results)
