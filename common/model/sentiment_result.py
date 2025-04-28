from __future__ import annotations
from dataclasses import dataclass
import datetime
import random
from typing import List

import pandas as pd

from common.config.db_config import MONGODB_COLLECTION_SENTIMENT
from common.infrastructure.mongodb.mongodb_client import MongoDbClient
from common.model.daily_basis_model import DailyBasisModel

@dataclass
class SentimentResult(DailyBasisModel):
    ticker: str
    avg_score: float
    label: str

    def from_raw(item: dict) -> SentimentResult:
        dt = item["date"]
        if isinstance(dt, str):
            dt = datetime.date.fromisoformat(dt)

        return SentimentResult(
            ticker=item["ticker"],
            avg_score=float(item["avg_score"]),
            label=item["label"],
            date=dt
        )

    def to_dict(self) -> dict:
        return {
            "date": self.date.strftime("%Y-%m-%d"),
            "ticker": self.ticker,
            "avg_score": self.avg_score,
            "label": self.label
        }

if __name__ == "__main__":
    top10 = ['AAPL', 'MSFT', 'NVDA', 'AMZN', 'GOOG', 'GOOGL', 'META', 'BRK-B', 'TSLA', 'AVGO']
    dates = pd.date_range(start="2016-01-01", end="2025-04-27", freq="B")

    # 결과 저장 리스트
    sentiment_results: List[dict] = []

    # 생성
    for date in dates:
        for ticker in top10:
            if random.random() < 0.5:
                avg_score = 0.0
                label = "Neutral"
            else:
                avg_score = random.uniform(-1, 1)
                if avg_score > 0:
                    label = "Positive"
                else:
                    label = "Negative"

            result = SentimentResult(
                ticker=ticker,
                avg_score=round(avg_score, 4),
                label=label,
                date=date.date()
            )
            sentiment_results.append(result.to_dict())

    mongo = MongoDbClient()
    mongo.insert_many(MONGODB_COLLECTION_SENTIMENT, sentiment_results)