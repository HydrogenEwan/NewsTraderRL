import unittest
import pandas as pd
import tempfile
import os
from datetime import datetime
from data.financial_news.financial_csv_news_fetcher import FinancialCsvNewsFetcher
from data.financial_news.financial_news_parser import FinancialNewsParser


class TestFinancialCsvNewsFetcher(unittest.TestCase):
    def setUp(self):
        # create test data
        self.test_data = pd.DataFrame({
            'id1': [1, 2, 3],
            'ticker': ['AAPL', 'GOOGL', 'AAPL'],
            'id2': [101, 102, 103],
            'datetime': [
                '2024-01-01 00:00:00',  # 1704067200
                '2024-01-02 00:00:00',  # 1704153600
                '2024-01-03 00:00:00'   # 1704240000
            ],
            'headline': [
                'Apple News 1',
                'Google News 1',
                'Apple News 2'
            ],
            'summary': [
                'Summary 1',
                'Summary 2',
                'Summary 3'
            ]
        })

        # create temporary CSV file
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.csv')
        self.test_data.to_csv(self.temp_file.name, index=False)
        self.csv_path = self.temp_file.name

        # create parser and fetcher
        self.parser = FinancialNewsParser()
        self.fetcher = FinancialCsvNewsFetcher(self.parser, self.csv_path)

    def tearDown(self):
        # clean up temporary file
        os.unlink(self.csv_path)

    def test_fetch_all_data(self):
        # test fetch all data
        news_list = list(self.fetcher.fetch('2024-01-01', '2024-12-31'))
        self.assertEqual(len(news_list), 3)
        
        # verify first data
        first_news = news_list[0]
        self.assertEqual(first_news.ticker, 'AAPL')
        self.assertEqual(first_news.headline, 'Apple News 1')
        self.assertEqual(first_news.summary, 'Summary 1')
        self.assertEqual(first_news.datetime, 1704067200)

    def test_fetch_with_ticker_filter(self):
        # test fetch data with ticker filter
        fetcher = FinancialCsvNewsFetcher(self.parser, self.csv_path, ticker='AAPL')
        news_list = list(fetcher.fetch('2024-01-01', '2024-12-31'))
        self.assertEqual(len(news_list), 2)
        
        # verify all news are AAPL
        for news in news_list:
            self.assertEqual(news.ticker, 'AAPL')

    def test_fetch_with_date_range(self):
        # test fetch data with date range filter
        news_list = list(self.fetcher.fetch('2024-01-02', '2024-01-02'))
        self.assertEqual(len(news_list), 1)
        self.assertEqual(news_list[0].headline, 'Google News 1')
        self.assertEqual(news_list[0].datetime, 1704153600)

    def test_fetch_empty_result(self):
        # test fetch data with empty result
        news_list = list(self.fetcher.fetch('2023-01-01', '2023-12-31'))
        self.assertEqual(len(news_list), 0)

    def test_fetch_invalid_date_range(self):
        # test fetch data with invalid date range
        news_list = list(self.fetcher.fetch('2024-01-02', '2024-01-01'))
        self.assertEqual(len(news_list), 0)

    def test_fetch_with_invalid_ticker(self):
        # test fetch data with invalid ticker
        fetcher = FinancialCsvNewsFetcher(self.parser, self.csv_path, ticker='INVALID')
        news_list = list(fetcher.fetch('2024-01-01', '2024-12-31'))
        self.assertEqual(len(news_list), 0)


if __name__ == '__main__':
    unittest.main() 