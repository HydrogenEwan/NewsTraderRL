from __future__ import annotations
from dataclasses import dataclass
import datetime

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