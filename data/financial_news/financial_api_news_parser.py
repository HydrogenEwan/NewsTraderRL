from typing import Dict, Optional
from datetime import datetime
import hashlib
from common.interface.data_parser import DataParser
from common.model.financial_news import FinancialNews

class FinancialApiNewsParser(DataParser):
    """parse news data from Finnhub API"""
    
    def parse(self, raw_data: Dict) -> Optional[FinancialNews]:
        """
        parse raw news data
        
        Args:
            raw_data: raw news data, contains the following fields:
                - category: news category
                - datetime: timestamp
                - headline: news headline
                - id: news id
                - image: thumbnail url
                - related: related stocks and companies
                - source: news source
                - summary: news summary
                - url: original url
                
        Returns:
            Optional[FinancialNews]: parsed news object, return None if parsing fails
        """
        try:
            # extract necessary fields
            ts = raw_data.get('datetime')
            if not ts:
                return None
                
            headline = raw_data.get('headline', '')
            ticker = raw_data.get('related', '')
            
            # generate news id
            content = f"{headline}|{ts}|{ticker}".encode('utf-8')
            news_id = hashlib.md5(content).hexdigest()
            
            # create date object
            news_date = datetime.fromtimestamp(ts).date()
            
            # create news object
            return FinancialNews(
                id=news_id,
                datetime=ts,
                headline=headline,
                summary=raw_data.get('summary'),
                ticker=ticker,
                date=news_date
            )
        except Exception as e:
            print(f"failed to parse news data: {e}")
            return None
