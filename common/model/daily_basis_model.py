from abc import ABC
from dataclasses import dataclass
from datetime import date

@dataclass
class DailyBasisModel(ABC):
    date: date
