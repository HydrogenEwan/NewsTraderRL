import unittest
from datetime import datetime
import hashlib
from data.financial_news.financial_api_news_parser import FinancialApiNewsParser
from common.model.financial_news import FinancialNews

class TestFinancialApiNewsParser(unittest.TestCase):
    def setUp(self):
        self.parser = FinancialApiNewsParser()
        
        # valid news data
        self.valid_news_data = {
            "category": "company news",
            "datetime": 1569550360,
            "headline": "More sops needed to boost electronic manufacturing: Top govt official",
            "id": 25286,
            "image": "https://img.etimg.com/thumb/msid-71321314,width-1070,height-580,imgsize-481831,overlay-economictimes/photo.jpg",
            "related": "AAPL",
            "source": "The Economic Times India",
            "summary": "NEW DELHI | CHENNAI: India may have to offer electronic manufacturers additional sops such as cheap credit and incentives for export along with infrastructure support in order to boost production and help the sector compete with China, Vietnam and Thailand, according to a top government official.",
            "url": "https://economictimes.indiatimes.com/industry/cons-products/electronics/more-sops-needed-to-boost-electronic-manufacturing-top-govt-official/articleshow/71321308.cms"
        }
        
        # news data with missing required fields
        self.invalid_news_data = {
            "category": "company news",
            "headline": "Test Headline",
            "source": "Test Source"
        }
        
    def test_parse_valid_data(self):
        # parse valid news data
        news = self.parser.parse(self.valid_news_data)
        
        # verify result
        self.assertIsInstance(news, FinancialNews)
        
        # verify news id generation
        expected_content = f"{self.valid_news_data['headline']}|{self.valid_news_data['datetime']}|{self.valid_news_data['related']}".encode('utf-8')
        expected_id = hashlib.md5(expected_content).hexdigest()
        self.assertEqual(news.id, expected_id)
        
        # verify other fields
        self.assertEqual(news.datetime, 1569550360)
        self.assertEqual(news.headline, "More sops needed to boost electronic manufacturing: Top govt official")
        self.assertEqual(news.summary, "NEW DELHI | CHENNAI: India may have to offer electronic manufacturers additional sops such as cheap credit and incentives for export along with infrastructure support in order to boost production and help the sector compete with China, Vietnam and Thailand, according to a top government official.")
        self.assertEqual(news.ticker, "AAPL")
        self.assertEqual(news.date, datetime.fromtimestamp(1569550360).date())
        
    def test_parse_invalid_data(self):
        # parse invalid news data
        news = self.parser.parse(self.invalid_news_data)
        
        # verify result is None
        self.assertIsNone(news)
        
    def test_parse_empty_data(self):
        # parse empty data
        news = self.parser.parse({})
        
        # verify result is None
        self.assertIsNone(news)
        
if __name__ == '__main__':
    unittest.main() 