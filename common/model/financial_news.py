from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from datetime import datetime, date

from common.model.daily_basis_model import DailyBasisModel


@dataclass
class FinancialNews(DailyBasisModel):
    id: int
    category: str
    datetime: int
    headline: str
    image: Optional[str]
    related: str
    source: str
    summary: Optional[str]
    url: str
    ticker: str

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "category": self.category,
            "datetime": self.datetime,
            "date": self.date.isoformat(),
            "headline": self.headline,
            "image": self.image,
            "related": self.related,
            "source": self.source,
            "summary": self.summary,
            "url": self.url,
            "ticker": self.ticker
        }

    @staticmethod
    def from_raw(item: dict) -> FinancialNews:
        ts = item["datetime"]
        return FinancialNews(
            id=item["id"],
            category=item["category"],
            datetime=ts,
            date=datetime.fromtimestamp(ts).date(),
            headline=item["headline"],
            image=item.get("image"),
            related=item["related"],
            source=item["source"],
            summary=item.get("summary"),
            url=item["url"],
            ticker=item["ticker"]
        )