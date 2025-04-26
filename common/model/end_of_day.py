from __future__ import annotations
from dataclasses import dataclass
from common.model.daily_basis_model import DailyBasisModel


@dataclass
class EndOfDayEvent(DailyBasisModel):
    source: str

    @staticmethod
    def from_raw(item: dict) -> EndOfDayEvent:
        return EndOfDayEvent(
            date=item.get("date"),
            source=item.get("source")
        )

    def to_dict(self) -> dict:
        return {
            "date": self.date.strftime("%Y-%m-%d"),
            "source": self.source,
        }