from dataclasses import dataclass
from typing import Any


@dataclass
class WebResponse:
    result: bool
    data: Any = None
    error: str = None

    def to_dict(self) -> dict:
        response = {
            "result": self.result,
        }

        if self.data is not None:
            if isinstance(self.data, list):
                response["data"] = [item.to_dict() if hasattr(item, "to_dict") else item for item in self.data]
            else:
                response["data"] = self.data.to_dict() if hasattr(self.data, "to_dict") else self.data

        if self.error is not None:
            response["error"] = self.error

        return response