from abc import ABC, abstractmethod


class ChangeStreamHandler(ABC):
    def on_insert(self, change: dict):
        pass