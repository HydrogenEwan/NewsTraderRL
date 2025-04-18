from abc import ABC, abstractmethod


class ChangeStreamHandler(ABC):
    @abstractmethod
    def on_insert(self, change: dict):
        pass