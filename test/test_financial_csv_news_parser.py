import unittest
from data.financial_news.financial_csv_news_parser import FinancialCsvNewsParser


class TestFinancialCsvNewsParser(unittest.TestCase):
    def setUp(self):
        self.parser = FinancialCsvNewsParser()
        self.test_data = {
            'id1': 1,
            'ticker': 'AAPL',
            'id2': 101,
            'datetime': 1704067200,  # 2024-01-01 00:00:00
            'headline': 'Test News Headline',
            'summary': 'Test News Summary'
        }

    def test_parse_valid_data(self):
        # test parse valid data
        news = self.parser.parse(self.test_data)
        self.assertIsNotNone(news)
        self.assertEqual(news.ticker, 'AAPL')
        self.assertEqual(news.datetime, 1704067200)
        self.assertEqual(news.headline, 'Test News Headline')
        self.assertEqual(news.summary, 'Test News Summary')

    def test_parse_without_summary(self):
        # test parse data without summary
        data = self.test_data.copy()
        del data['summary']
        news = self.parser.parse(data)
        self.assertIsNotNone(news)
        self.assertIsNone(news.summary)
        self.assertEqual(news.ticker, 'AAPL')

    def test_parse_missing_required_fields(self):
        # test parse data missing required fields
        required_fields = ['datetime', 'headline', 'ticker']
        for field in required_fields:
            data = self.test_data.copy()
            del data[field]
            news = self.parser.parse(data)
            self.assertIsNone(news, f"Should return None when {field} is missing")

    def test_parse_with_extra_fields(self):
        # test parse data with extra fields
        data = self.test_data.copy()
        data['extra_field'] = 'extra value'
        news = self.parser.parse(data)
        self.assertIsNotNone(news)
        self.assertEqual(news.ticker, 'AAPL')

    def test_parse_with_different_id_fields(self):
        # test parse data with different id fields
        data = self.test_data.copy()
        data['id1'] = 999
        data['id2'] = 888
        news1 = self.parser.parse(data)
        
        data['id1'] = 777
        data['id2'] = 666
        news2 = self.parser.parse(data)
        
        self.assertEqual(news1.id, news2.id)  # ID should be generated based on content, not original ID


if __name__ == '__main__':
    unittest.main() 