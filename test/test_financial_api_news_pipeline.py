import unittest
import os
import json
from datetime import datetime
from unittest.mock import Mock, patch
from data.financial_news.financial_api_news_pipeline import FinancialApiNewsPipeline
from data.financial_news.financial_api_news_fetcher import FinancialApiNewsFetcher
from common.model.financial_news import FinancialNews
from finnhub import Client

class TestFinancialApiNewsPipeline(unittest.TestCase):
    def setUp(self):
        self.api_key = "test_api_key"
        self.output_dir = "test/test_output"
        self.pipeline = FinancialApiNewsPipeline(self.api_key, self.output_dir)
        
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
            }
        ]
        
    def tearDown(self):
        # clean up test output directory
        if os.path.exists(self.output_dir):
            for file in os.listdir(self.output_dir):
                os.remove(os.path.join(self.output_dir, file))
            os.rmdir(self.output_dir)
            
    @patch('finnhub.Client')
    def test_process(self, mock_client_class):
        # set up mock Finnhub client
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.company_news.return_value = self.mock_news_data
        
        # process news data
        news_list = list(self.pipeline.process("AAPL", "2019-09-25", "2019-09-26"))
        
        # verify result
        self.assertEqual(len(news_list), 1)
        self.assertIsInstance(news_list[0], FinancialNews)
        self.assertEqual(news_list[0].headline, "More sops needed to boost electronic manufacturing: Top govt official")
        
        # verify mock object is called correctly
        mock_client.company_news.assert_called_once()
        
    def test_save_news(self):
        # create test news data
        news_list = [FinancialNews(
            id="test_id",
            datetime=1569550360,
            headline="Test Headline",
            summary="Test Summary",
            ticker="AAPL",
            date=datetime.fromtimestamp(1569550360).date()
        )]
        
        # save news data
        filepath = self.pipeline.save_news(news_list, "AAPL", "2019-09-25", "2019-09-26")
        
        # verify file is created
        self.assertTrue(os.path.exists(filepath))
        
        # verify file content
        with open(filepath, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
            
        self.assertEqual(len(saved_data), 1)
        self.assertEqual(saved_data[0]['headline'], "Test Headline")
        
    @patch('finnhub.Client')
    def test_run_success(self, mock_client_class):
        # set up mock Finnhub client
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.company_news.return_value = self.mock_news_data
        
        # run pipeline
        filepath = self.pipeline.run("AAPL", "2019-09-25", "2019-09-26")
        
        # verify result
        self.assertIsNotNone(filepath)
        self.assertTrue(os.path.exists(filepath))
        
    @patch('finnhub.Client')
    def test_run_empty_result(self, mock_client_class):
        # set up mock Finnhub client to return empty result
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.company_news.return_value = []
        
        # run pipeline
        filepath = self.pipeline.run("AAPL", "2019-09-25", "2019-09-26")
        
        # verify result
        self.assertIsNone(filepath)
        
if __name__ == '__main__':
    unittest.main() 