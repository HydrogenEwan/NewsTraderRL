from common.interface.data_parser import DataParser
from common.model.financial_news import FinancialNews


class FinancialNewsParser(DataParser):
    def parse(self, raw: dict) -> FinancialNews:
        return FinancialNews.from_raw(raw)