from dataclasses import dataclass
from typing import Any, List, Optional

from common.model.financial_news import FinancialNews


@dataclass
class CompanyProfile:
    address: str
    city: str
    country: str
    currency: str
    cusip: str
    description: str
    employee_total: int
    estimate_currency: str
    exchange: str
    finnhub_industry: str
    floating_share: float
    fundamental_freq: str
    ggroup: str
    gind: str
    gsector: str
    gsubind: str
    insider_ownership: float
    institution_ownership: float
    ipo: str
    ir_url: str
    isin: str
    lei: str
    logo: str
    market_cap_currency: str
    market_capitalization: float
    naics: str
    naics_national_industry: str
    naics_sector: str
    naics_subsector: str
    name: str
    phone: str
    sedol: str
    share_outstanding: float
    state: str
    ticker: str
    us_share: int
    weburl: str

    @staticmethod
    def from_raw(doc: dict) -> "CompanyProfile":
        return CompanyProfile(
            address=doc["address"],
            city=doc["city"],
            country=doc["country"],
            currency=doc["currency"],
            cusip=doc["cusip"],
            description=doc["description"],
            employee_total=doc["employeeTotal"],
            estimate_currency=doc["estimateCurrency"],
            exchange=doc["exchange"],
            finnhub_industry=doc["finnhubIndustry"],
            floating_share=doc["floatingShare"],
            fundamental_freq=doc["fundamentalFreq"],
            ggroup=doc["ggroup"],
            gind=doc["gind"],
            gsector=doc["gsector"],
            gsubind=doc["gsubind"],
            insider_ownership=doc["insiderOwnership"],
            institution_ownership=doc["institutionOwnership"],
            ipo=doc["ipo"],
            ir_url=doc["irUrl"],
            isin=doc["isin"],
            lei=doc["lei"],
            logo=doc["logo"],
            market_cap_currency=doc["marketCapCurrency"],
            market_capitalization=doc["marketCapitalization"],
            naics=doc["naics"],
            naics_national_industry=doc["naicsNationalIndustry"],
            naics_sector=doc["naicsSector"],
            naics_subsector=doc["naicsSubsector"],
            name=doc["name"],
            phone=doc["phone"],
            sedol=doc["sedol"],
            share_outstanding=doc["shareOutstanding"],
            state=doc["state"],
            ticker=doc["ticker"],
            us_share=doc["usShare"],
            weburl=doc["weburl"],
        )

    def to_dict(self) -> dict:
        return {
            "address": self.address,
            "city": self.city,
            "country": self.country,
            "currency": self.currency,
            "cusip": self.cusip,
            "description": self.description,
            "employee_total": self.employee_total,
            "estimate_currency": self.estimate_currency,
            "exchange": self.exchange,
            "finnhub_industry": self.finnhub_industry,
            "floating_share": self.floating_share,
            "fundamental_freq": self.fundamental_freq,
            "ggroup": self.ggroup,
            "gind": self.gind,
            "gsector": self.gsector,
            "gsubind": self.gsubind,
            "insider_ownership": self.insider_ownership,
            "institution_ownership": self.institution_ownership,
            "ipo": self.ipo,
            "ir_url": self.ir_url,
            "isin": self.isin,
            "lei": self.lei,
            "logo": self.logo,
            "market_cap_currency": self.market_cap_currency,
            "market_capitalization": self.market_capitalization,
            "naics": self.naics,
            "naics_national_industry": self.naics_national_industry,
            "naics_sector": self.naics_sector,
            "naics_subsector": self.naics_subsector,
            "name": self.name,
            "phone": self.phone,
            "sedol": self.sedol,
            "share_outstanding": self.share_outstanding,
            "state": self.state,
            "ticker": self.ticker,
            "us_share": self.us_share,
            "weburl": self.weburl,
        }


@dataclass
class TickerWeight:
    date: str
    weight: float

    def to_dict(self) -> dict:
        return {
            "date": self.date,
            "weight": self.weight
        }


@dataclass
class TickerDetailResponse:
    ticker: str
    weight: float
    returns: float
    sentiment: float
    chart: List[TickerWeight]
    news: List[FinancialNews]
    company_profile: CompanyProfile

    def to_dict(self) -> dict:
        return {
            "ticker": self.ticker,
            "weight": self.weight,
            "returns": self.returns,
            "sentiment": self.sentiment,
            "chart": [w.to_dict() for w in self.chart],
            "news": [n.to_dict() for n in self.news],
            "company_profile": self.company_profile.to_dict()
        }
