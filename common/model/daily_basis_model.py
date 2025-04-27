from abc import ABC
from dataclasses import dataclass, field
import datetime

@dataclass
class DailyBasisModel(ABC):
    date: datetime.date = field()

    def __post_init__(self):
        if isinstance(self.date, str):
            try:
                self.date = datetime.date.fromisoformat(self.date)
            except ValueError as e:
                raise ValueError(f"Invalid date format for '{self.date}', expected YYYY-MM-DD") from e