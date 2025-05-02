import client from "./client";

export interface Portfolio {
  date: string;
  date_index: number;
  expected_return: number;
  long_ratio: number;
  rounded_weights: Array<number>;
  tickers: Array<string>;
}

export const getPortfolio = async (date?: string | undefined) =>
  await client<Portfolio>(
    `portfolio${date !== undefined ? `?date=${date}` : ""}`,
    "GET"
  );

export interface Ticker {
  ticker: string;
  weight: number;
  chart: Array<{ date: string; weight: number }>;
  company_profile: {
    address: string;
    city: string;
    country: string;
    currency: string;
    cusip: string;
    description: string;
    employee_total: number;
    estimate_currency: string;
    exchange: string; // exchange
    finnhub_industry: string;
    floating_share: number;
    fundamental_freq: string;
    ggroup: string;
    gind: string;
    gsector: string; // Sector
    gsubind: string;
    insider_ownership: number;
    institution_ownership: number;
    ipo: string;
    ir_url: string;
    isin: string;
    lei: string;
    logo: string;
    market_cap_currency: string;
    market_capitalization: number; // Market Cap
    naics: string;
    naics_national_industry: string;
    naics_sector: string;
    naics_subsector: string;
    name: string; // 로고옆
    phone: string;
    sedol: string;
    share_outstanding: number;
    state: string;
    ticker: string; //Ticker
    us_share: number;
    weburl: string;
  };
  news: Array<{
    date: string;
    datetime: 1449532800;
    headline: string;
    id: string;
    summary: string;
    ticker: string;
  }>;
  sentiment: {
    avg_score: number;
    label: string;
  };
}
export const getDetail = async (ticker: string) =>
  await client<Ticker>(`ticker/${ticker}`, "GET");
