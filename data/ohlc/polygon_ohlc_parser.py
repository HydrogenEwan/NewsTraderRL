from typing import Any
from datetime import datetime

from common.interface.data_parser import DataParser
from common.model.ohlc import Ohlc

class PolygonOhlcParser(DataParser):
    def __init__(self, ticker: str):
        self.ticker = ticker

    def parse(self, bar: Any) -> Ohlc:
        # bar["t"]는 밀리초 단위 UNIX timestamp
        dt = datetime.utcfromtimestamp(bar["t"] / 1000)
        return Ohlc(
            ticker=self.ticker,
            date=dt,
            open=float(bar["o"]),
            high=float(bar["h"]),
            low=float(bar["l"]),
            close=float(bar["c"]),
            volume=int(bar["v"]),
            turnover=float(bar["c"]) * int(bar["v"])
        )
