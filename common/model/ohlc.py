from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from datetime import datetime
from common.model.daily_basis_model import DailyBasisModel


@dataclass
class Ohlc(DailyBasisModel):
    ticker: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    marketcap: float

    @staticmethod
    def from_yfinance_row(row: Any, ticker: str, marketcap: float) -> Ohlc:
        mc = float(marketcap)
        return Ohlc(
            ticker=ticker,
            date=row["Date"].to_pydatetime().date(),
            open=float(row["Open"]),
            high=float(row["High"]),
            low=float(row["Low"]),
            close=float(row["Close"]),
            volume=int(row["Volume"]),
            marketcap=mc
        )

    @staticmethod
    def from_raw(doc: dict) -> Ohlc:
        dt = doc["date"]
        if isinstance(dt, str):
            dt = datetime.strptime(dt, "%Y-%m-%d").date()

        return Ohlc(
            ticker=doc["ticker"],
            date=dt,
            open=float(doc["open"]),
            high=float(doc["high"]),
            low=float(doc["low"]),
            close=float(doc["close"]),
            volume=int(doc["volume"]),
            marketcap=float(doc["marketcap"])
        )

    def to_dict(self) -> dict:
        return {
            "ticker": self.ticker,
            "date": self.date.strftime("%Y-%m-%d"),
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "marketcap": float(self.marketcap)
        }