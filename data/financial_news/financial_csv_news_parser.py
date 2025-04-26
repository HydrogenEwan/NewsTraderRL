from typing import Optional
from common.interface.data_parser import DataParser
from common.model.financial_news import FinancialNews


class FinancialCsvNewsParser(DataParser):
    def parse(self, raw: dict) -> Optional[FinancialNews]:
        # check required fields
        if not all(key in raw for key in ['datetime', 'headline', 'ticker']):
            return None

        # generate news id based on content
        return FinancialNews.from_raw({
            'datetime': int(raw['datetime']),  # already converted to timestamp in fetcher
            'headline': raw['headline'],
            'summary': raw.get('summary'),  # optional field
            'ticker': raw['ticker']
        })
