"""SEC data model module.

This module provides the SecData class for handling SEC filing data.
It includes functionality for converting between dictionary and object formats,
and handles data fields like filing ID, date, text content and ticker symbol.
"""

from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime

from common.model.daily_basis_model import DailyBasisModel


@dataclass
class SecData(DailyBasisModel):
    '''Schema for SEC data'''
    id: int
    datetime: int # timestamp
    text: str
    ticker: str
    date: str

    def to_dict(self) -> dict:
        """Convert SecData object to dictionary format.
        
        Returns:
            dict: Dictionary containing SEC data fields including id, datetime, date and ticker
        """
        return {
            "id": self.id,
            "text": self.text,
            "datetime": self.datetime,
            "date": self.date.isoformat() if self.date else None,
            "ticker": self.ticker
        }

    @staticmethod
    def from_raw(item: dict) -> SecData:
        """Create a SecData object from a dictionary.

        Args:
            item (dict): Dictionary containing SEC data fields
                including id, datetime, date and ticker

        Returns:
            SecData: SecData object created from the dictionary
        """
        return SecData(
            id=item["id"],
            datetime=item["datetime"],
            date=item["date"],
            text=item["text"],
            ticker=item["ticker"]
        )
