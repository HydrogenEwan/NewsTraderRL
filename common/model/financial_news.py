from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from datetime import datetime, date
import hashlib

from common.model.daily_basis_model import DailyBasisModel


@dataclass
class FinancialNews(DailyBasisModel):
    id: str
    datetime: int
    headline: str
    summary: Optional[str]
    ticker: str
    date: date

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "datetime": self.datetime,
            "headline": self.headline,
            "summary": self.summary,
            "ticker": self.ticker,
            "date": self.date.isoformat()
        }

    @staticmethod
    def from_raw(item: dict) -> Optional[FinancialNews]:
        ts = item.get("datetime", 0)
        if not ts:
            return None  # Discard news without valid datetime

        headline = item.get("headline", "")
        ticker = item.get("symbol", item.get("ticker", ""))
        
        # generate news id based on news content
        content = f"{headline}|{ts}|{ticker}".encode('utf-8')
        news_id = hashlib.md5(content).hexdigest()

        # create date object from timestamp
        news_date = datetime.fromtimestamp(ts).date()

        return FinancialNews(
            id=news_id,
            datetime=ts,
            headline=item.get("headline", ""),
            summary=item.get("summary"),
            ticker=item.get("symbol", item.get("ticker", "")),
            date=news_date  # add date parameter
        )
