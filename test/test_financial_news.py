import unittest
from datetime import datetime
from common.model.financial_news import FinancialNews

class TestFinancialNews(unittest.TestCase):
    def setUp(self):
        # create test data
        self.test_data = {
            "datetime": 1714060800,  # 2024-03-26 00:00:00
            "headline": "Test News Headline",
            "summary": "Test News Summary",
            "ticker": "AAPL"
        }

    def test_from_raw_with_valid_data(self):
        # test creating news object from raw data
        news = FinancialNews.from_raw(self.test_data)
        self.assertIsNotNone(news)
        self.assertEqual(news.headline, "Test News Headline")
        self.assertEqual(news.summary, "Test News Summary")
        self.assertEqual(news.ticker, "AAPL")
        self.assertEqual(news.datetime, 1714060800)

    def test_from_raw_without_datetime(self):
        # test creating news object from raw data without datetime
        invalid_data = self.test_data.copy()
        del invalid_data["datetime"]
        news = FinancialNews.from_raw(invalid_data)
        self.assertIsNone(news)

    def test_id_consistency(self):
        # test generating same id for same content
        news1 = FinancialNews.from_raw(self.test_data)
        news2 = FinancialNews.from_raw(self.test_data)
        self.assertEqual(news1.id, news2.id)

    def test_id_uniqueness(self):
        # test generating different id for different content
        news1 = FinancialNews.from_raw(self.test_data)
        
        # modify headline
        different_headline = self.test_data.copy()
        different_headline["headline"] = "Different Headline"
        news2 = FinancialNews.from_raw(different_headline)
        
        # modify timestamp
        different_time = self.test_data.copy()
        different_time["datetime"] = 1714060801
        news3 = FinancialNews.from_raw(different_time)
        
        # modify stock code
        different_ticker = self.test_data.copy()
        different_ticker["ticker"] = "GOOGL"
        news4 = FinancialNews.from_raw(different_ticker)
        
        # verify all ids are different
        ids = {news1.id, news2.id, news3.id, news4.id}
        self.assertEqual(len(ids), 4)

    def test_to_dict(self):
        # test converting to dict
        news = FinancialNews.from_raw(self.test_data)
        news_dict = news.to_dict()
        
        self.assertEqual(news_dict["headline"], "Test News Headline")
        self.assertEqual(news_dict["summary"], "Test News Summary")
        self.assertEqual(news_dict["ticker"], "AAPL")
        self.assertEqual(news_dict["datetime"], 1714060800)
        self.assertEqual(news_dict["id"], news.id)

if __name__ == '__main__':
    unittest.main() 