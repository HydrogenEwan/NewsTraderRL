from abc import ABC, abstractmethod
from typing import Any


class DataParser(ABC):
    @abstractmethod
    def parse(self, data: Any) -> Any:
        """
        Parse the data
        :return: any type of data class
        """
        pass