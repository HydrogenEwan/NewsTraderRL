from common.interface.data_pipeline import DataPipeline
from common.model.simulation import SimulationItem
from common.config.db_config import MONGODB_COLLECTION_NEWS
from data.sec.sec_fetcher import SecFetcher
from data.sec.sec_parser import SecParser

TICKERS = ["AAPL", "GOOG", "MSFT"] # TODO: change it to actual
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
    def __init__(self):
        super().__init__()
        self.parser = SecParser()
        self.fetcher = SecFetcher(self.parser, TICKERS)
        self.collection = "sec_data"
        self.dummy = "sec_test"

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
        sec_batch = self.batch_iterator(sec_data, batch_size)
        for batch in sec_batch:
            # print(f"batch: {batch}")
            print(f"batch type: {type(batch)}")
            print(f"batch[0] type: {type(batch[0])}")
            self.client.insert_many(self.dummy, batch)

    def run_simulation_pipeline(self, ticker: str, start: str, end: str, batch_size: int = 100):
        pass
