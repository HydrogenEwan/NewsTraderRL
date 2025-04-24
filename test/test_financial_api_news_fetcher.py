import unittest
from datetime import datetime
import pandas as pd
from unittest.mock import Mock, patch
from data.financial_news.financial_api_news_fetcher import FinancialApiNewsFetcher
from data.financial_news.financial_news_parser import FinancialNewsParser
from common.model.financial_news import FinancialNews

class TestFinancialApiNewsFetcher(unittest.TestCase):
    def setUp(self):
        self.parser = FinancialNewsParser()
        self.api_key = "test_api_key"
        self.ticker = "AAPL"
        
        # create mock finnhub client
        self.mock_client = Mock()
        self.fetcher = FinancialApiNewsFetcher(self.parser, self.api_key, self.ticker)
        self.fetcher.client = self.mock_client
        
        # mock news data
        self.mock_news_data = [
            {
                "category": "company news",
                "datetime": 1569550360,
                "headline": "More sops needed to boost electronic manufacturing: Top govt official",
                "id": 25286,
                "image": "https://img.etimg.com/thumb/msid-71321314,width-1070,height-580,imgsize-481831,overlay-economictimes/photo.jpg",
                "related": "AAPL",
                "source": "The Economic Times India",
                "summary": "NEW DELHI | CHENNAI: India may have to offer electronic manufacturers additional sops such as cheap credit and incentives for export along with infrastructure support in order to boost production and help the sector compete with China, Vietnam and Thailand, according to a top government official.",
                "url": "https://economictimes.indiatimes.com/industry/cons-products/electronics/more-sops-needed-to-boost-electronic-manufacturing-top-govt-official/articleshow/71321308.cms"
            },
            {
                "category": "company news",
                "datetime": 1569528720,
                "headline": "How to disable comments on your YouTube videos in 2 different ways",
                "id": 25287,
                "image": "https://amp.businessinsider.com/images/5d8d16182e22af6ab66c09e9-1536-768.jpg",
                "related": "AAPL",
                "source": "Business Insider",
                "summary": "You can disable comments on your own YouTube video if you don't want people to comment on it. It's easy to disable comments on YouTube by adjusting the settings for one of your videos in the beta or classic version of YouTube Studio.",
                "url": "https://www.businessinsider.com/how-to-disable-comments-on-youtube"
            },
            {
                "category": "company news",
                "datetime": 1569526180,
                "headline": "Apple iPhone 11 Pro Teardowns Look Encouraging for STMicro and Sony",
                "id": 25341,
                "image": "http://s.thestreet.com/files/tsc/v2008/photos/contrib/uploads/ba140938-d409-11e9-822b-fda891ce1fc1.png",
                "related": "AAPL",
                "source": "TheStreet",
                "summary": "STMicroelectronics and Sony each appear to be supplying four chips for Apple's latest flagship iPhones. Many other historical iPhone suppliers also make appearances in the latest teardowns….STM",
                "url": "https://realmoney.thestreet.com/investing/technology/iphone-11-pro-teardowns-look-encouraging-for-stmicro-sony-15105767"
            }
        ]
        
    def test_fetch_with_ticker(self):
        # set mock client
        self.mock_client.company_news.return_value = self.mock_news_data
        
        # fetch news
        news_list = list(self.fetcher.fetch("2019-09-25", "2019-09-26"))
        
        # verify result
        self.assertEqual(len(news_list), 3)
        self.assertIsInstance(news_list[0], FinancialNews)
        self.assertEqual(news_list[0].headline, "More sops needed to boost electronic manufacturing: Top govt official")
        self.assertEqual(news_list[1].headline, "How to disable comments on your YouTube videos in 2 different ways")
        self.assertEqual(news_list[2].headline, "Apple iPhone 11 Pro Teardowns Look Encouraging for STMicro and Sony")
        
        # verify api call
        self.mock_client.company_news.assert_called_once_with(
            self.ticker,
            _from="2019-09-25",
            to="2019-09-26"
        )
        
    def test_fetch_without_ticker(self):
        # create fetcher without ticker
        fetcher = FinancialApiNewsFetcher(self.parser, self.api_key)
        
        # verify exception is raised
        with self.assertRaises(ValueError) as context:
            list(fetcher.fetch("2019-09-25", "2019-09-26"))
            
        self.assertEqual(str(context.exception), "must specify ticker when using Finnhub API")
        
    def test_fetch_empty_response(self):
        # set mock client to return empty list
        self.mock_client.company_news.return_value = []
        
        # fetch news
        news_list = list(self.fetcher.fetch("2019-09-25", "2019-09-26"))
        
        # verify result is empty
        self.assertEqual(len(news_list), 0)
        
if __name__ == '__main__':
    unittest.main() 