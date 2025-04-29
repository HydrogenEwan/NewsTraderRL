"""
SEC Pipeline Documentation

This module provides functionality for fetching and processing SEC filings data through a pipeline system.

The main components are:
- SecPipeline: Main pipeline class for handling SEC data
- Historical data fetching and processing
- Simulation data processing
- Database integration for storing SEC filings

Key Features:
- Fetches SEC filings for specified date ranges and tickers
- Processes and parses raw SEC filing data
- Stores processed data in MongoDB
- Supports batch processing for large datasets
- Provides simulation capabilities for backtesting

Dependencies:
- typing
- common.interface.data_pipeline
- common.model.simulation
- common.config.target_tickers
- data.sec.sec_fetcher
- data.sec.sec_parser

Example Usage:
    pipeline = SecPipeline()
    pipeline.run_historical_pipeline(
        start="2023-01-01",
        end="2023-12-31",
        tickers=["AAPL", "GOOGL"],
        batch_size=100
    )
"""

from tqdm import tqdm
from typing import Iterator

from common.config.db_config import MONGODB_COLLECTION_SEC
from common.interface.data_pipeline import DataPipeline
from common.model.simulation import SimulationItem
from common.config.target_tickers import TARGET_TICKERS
from data.sec.sec_fetcher import SecFetcher
from data.sec.sec_parser import SecParser


# TODO:Should we include the db credential to env
# TODO: Fixed ticker? or should we fetch with some ticker
class SecPipeline(DataPipeline):
    """
    A pipeline for fetching and processing SEC filings data.

    This class implements the DataPipeline interface to handle SEC filings data.
    It provides functionality to fetch historical SEC filings data and process it
    for simulation purposes.

    Attributes:
        parser (SecParser): Parser for SEC filings data
        fetcher (SecFetcher): Fetcher for SEC filings data
        collection (str): MongoDB collection name for storing SEC data
        dummy (str): Name of simulation collection

    Methods:
        run_historical_pipeline: Fetches and stores historical SEC filings data
        run_simulation_pipeline: Processes SEC data for simulation purposes
    """
    def __init__(self, collection=MONGODB_COLLECTION_SEC):
        super().__init__()
        self.parser = SecParser()
        self.fetcher = SecFetcher(self.parser, TARGET_TICKERS)
        self.collection = collection

    def run_historical_pipeline(
        self,
        start: str,
        end: str,
        tickers: list[str] = None,
        batch_size: int = 100
    ) -> None:
        """
        Run historical pipeline to fetch and store SEC data.

        Args:
            ticker list[str]: Stock ticker symbol
            start (str): Start date in YYYY-MM-DD format
            end (str): End date in YYYY-MM-DD format  
            batch_size (int, optional): Number of records per batch. Defaults to 100.

        Returns:
            None
        """
        sec_data = self.fetcher.fetch(start, end, tickers)
        self.push_to_db(sec_data, batch_size)

    def push_to_db(self, sec_data: Iterator, batch_size: int = 100):
        """
        Push sec data to db.
        Args:
            sec_data (Iterator): Iterator of sec data
            batch_size (int, optional): Number of records per batch. Defaults to 100.
        Returns:
            None
        """
        sec_batch = self.batch_iterator(sec_data, batch_size)
        for batch in tqdm(sec_batch, desc="Pushing to MongoDB"):
            # print(f"batch: {batch}")
            print(f"batch type: {type(batch)}")
            print(f"batch[0] type: {type(batch[0])}")
            self.client.insert_many(self.collection, batch)

    def run_simulation_pipeline(self, ticker: str, start: str, end: str, batch_size: int = 100):
        pass


if __name__ == "__main__":
    pipeline = SecPipeline()
    pipeline.run_historical_pipeline(
        start="1999-01-01",
        end="2015-12-31",
        tickers=TARGET_TICKERS,
        batch_size=100
    )