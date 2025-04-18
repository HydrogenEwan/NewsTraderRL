from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from typing import Any


@dataclass
class Ohlc:
    ticker: str
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: int

    @staticmethod
    def from_yfinance_row(row: Any, ticker: str) -> Ohlc:
        return Ohlc(
            ticker=ticker,
            date=row["Date"].to_pydatetime().date(),
            open=float(row["Open"]),
            high=float(row["High"]),
            low=float(row["Low"]),
            close=float(row["Close"]),
            volume=int(row["Volume"])
        )

    def to_dict(self) -> dict:
        return {
            "ticker": self.ticker,
            "date": self.date,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume
        }
