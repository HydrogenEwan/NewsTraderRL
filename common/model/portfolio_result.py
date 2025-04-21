import unittest
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Union

@dataclass
class PortfolioResult:
    tickers: List[str]
    portfolio_weights: List[float]
    long_ratio: float
    expected_return: float
    date_index: int
    returns: List[float]
    error: Optional[str] = None
    traceback: Optional[str] = None


class PortfolioResults:
    def __init__(self):
        self.results: Dict[str, PortfolioResult] = {}

    def add_portfolio_result(self, date: str, result: PortfolioResult):
        self.results[date] = result

    def to_dict(self) -> Dict[str, dict]:
        return {
            date: result.__dict__ for date, result in self.results.items()
        }


# Test class for PortfolioResults
class TestPortfolioResults(unittest.TestCase):
    def test_to_dict(self):
        results = PortfolioResults()

        results.add_portfolio_result("2023-04-20", PortfolioResult(
            tickers=["AAPL", "AMD"],
            portfolio_weights=[0.3, -0.2],
            long_ratio=0.5,
            expected_return=0.0012,
            date_index=123,
            returns=[0.02, -0.01]
        ))

        results.add_portfolio_result("2023-04-21", PortfolioResult(
            tickers=[],
            portfolio_weights=[],
            long_ratio=0.0,
            expected_return=0.0,
            date_index=124,
            returns=[],
            error="Error processing date 2023-04-21",
            traceback="Fake traceback object"
        ))

        output = results.to_dict()

        self.assertIn("2023-04-20", output)
        self.assertIn("2023-04-21", output)
        self.assertEqual(output["2023-04-20"]["tickers"], ["AAPL", "AMD"])
        self.assertEqual(output["2023-04-21"]["error"], "Error processing date 2023-04-21")
        self.assertEqual(output["2023-04-21"]["traceback"], "Fake traceback object")

        import json
        print(json.dumps(output, indent=2))

if __name__ == '__main__':
    unittest.main()
