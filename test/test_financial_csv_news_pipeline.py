import unittest
import tempfile
import os
import pandas as pd
from datetime import datetime, timedelta
from data.financial_news.financial_csv_news_pipeline import FinancialCsvNewsPipeline
from common.model.financial_news import FinancialNews


class TestFinancialCsvNewsPipeline(unittest.TestCase):
    def setUp(self):
        # create temporary CSV file
        self.temp_dir = tempfile.mkdtemp()
        self.csv_path = os.path.join(self.temp_dir, "test_news.csv")
        
        # create test data
        self.test_data = pd.DataFrame({
            'datetime': [
                datetime.now() - timedelta(days=2),
                datetime.now() - timedelta(days=1),
                datetime.now(),
                datetime.now() + timedelta(days=1)
            ],
            'headline': ['News 1', 'News 2', 'News 3', 'News 4'],
            'summary': ['Summary 1', 'Summary 2', 'Summary 3', 'Summary 4'],
            'ticker': ['AAPL', 'AAPL', 'GOOGL', 'GOOGL']
        })
        self.test_data.to_csv(self.csv_path, index=False)
        
        # create pipeline instance
        self.pipeline = FinancialCsvNewsPipeline(self.csv_path)

    def tearDown(self):
        # clean up temporary file
        if os.path.exists(self.csv_path):
            os.remove(self.csv_path)
        os.rmdir(self.temp_dir)

    def test_process_all_data(self):
        # test process all data
        start = (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d')
        end = (datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d')
        
        news_list = list(self.pipeline.process(start, end))
        self.assertEqual(len(news_list), 4)
        self.assertTrue(all(isinstance(news, FinancialNews) for news in news_list))

    def test_process_with_ticker_filter(self):
        # test process with ticker filter
        pipeline = FinancialCsvNewsPipeline(self.csv_path, ticker='AAPL')
        start = (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d')
        end = (datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d')
        
        news_list = list(pipeline.process(start, end))
        self.assertEqual(len(news_list), 2)
        self.assertTrue(all(news.ticker == 'AAPL' for news in news_list))

    def test_get_news_by_ticker(self):
        # test get news by ticker
        start = (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d')
        end = (datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d')
        
        news_list = list(self.pipeline.get_news_by_ticker('GOOGL', start, end))
        self.assertEqual(len(news_list), 2)
        self.assertTrue(all(news.ticker == 'GOOGL' for news in news_list))

    def test_process_nonexistent_file(self):
        # test process nonexistent file
        pipeline = FinancialCsvNewsPipeline('nonexistent.csv')
        start = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        end = datetime.now().strftime('%Y-%m-%d')
        
        news_list = list(pipeline.process(start, end))
        self.assertEqual(len(news_list), 0)


if __name__ == '__main__':
    unittest.main() 