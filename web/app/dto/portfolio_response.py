from dataclasses import dataclass

from common.model.portfolio_result import PortfolioResult


class PortfolioResponse:
    def __init__(self, portfolio: PortfolioResult):
        self.portfolio = portfolio

    def to_dict(self) -> dict:
        result = self.portfolio.to_dict()
        result["rounded_weights"] = self.portfolio.round_and_adjust()
        return result