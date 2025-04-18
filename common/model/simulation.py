from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from typing import Any


@dataclass
class SimulationItem:
    data_type: str
    data: Any

    def to_dict(self) -> dict:
        return {
            "data_type": self.data_type,
            "data": self.data.to_dict() if hasattr(self.data, "to_dict") else self.data
        }

@dataclass
class Simulation:
    date: date
    items: list[SimulationItem]

    def to_dict(self) -> dict:
        return {
            "date": self.date,
            "items": [item.to_dict() for item in self.items]
        }
