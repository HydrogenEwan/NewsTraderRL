from common.interface.data_pipeline import DataPipeline
from common.model.simulation import SimulationItem
from common.config.db_config import MONGODB_COLLECTION_NEWS

class FinancialNewsPipeline(DataPipeline):
    def run_historical_pipeline(self, ticker: str, start: str, end: str, batch_size: int = 100):
        pass

    def run_simulation_pipeline(self, ticker: str, start: str, end: str, batch_size: int = 100):
        pass