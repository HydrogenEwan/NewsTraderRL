from abc import ABC
from dataclasses import dataclass, field
from datetime import date

@dataclass
class DailyBasisModel(ABC):
    date: date = field()

    def __post_init__(self):
        if isinstance(self.date, str):
            try:
                self.date = date.fromisoformat(self.date)
            except ValueError as e:
                raise ValueError(f"Invalid date format for '{self.date}', expected YYYY-MM-DD") from e