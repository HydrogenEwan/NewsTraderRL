from abc import ABC, abstractmethod
from typing import Any


class DataFetcher(ABC):
    @abstractmethod
    def fetch(self, start: str, end: str) -> list[Any]:
        """
        Fetch and return parsed objects.
        """
        pass
