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
    turnover: float

    # @staticmethod
    # def from_yfinance_row(row: Any, ticker: str) -> Ohlc:
    #     return Ohlc(
    #         ticker=ticker,
    #         date=row["Date"].to_pydatetime().date(),
    #         open=float(row["Open"]),
    #         high=float(row["High"]),
    #         low=float(row["Low"]),
    #         close=float(row["Close"]),
    #         volume=int(row["Volume"]),
    #         turnover=row["Close"] * int(row["Volume"])
    #     )

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
            turnover=float(doc["turnover"])
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
            "turnover": float(self.turnover)
        }