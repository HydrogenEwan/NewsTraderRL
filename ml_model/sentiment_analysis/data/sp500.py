import os
import time
import logging
import pandas as pd
from functools import lru_cache
from rapidfuzz import process, fuzz
from config import CONFIG

logger = logging.getLogger(__name__)

def get_sp500_list(force_update: bool = False) -> pd.DataFrame:
    cache_file = CONFIG["sp500_cache_file"]
    if not force_update and os.path.exists(cache_file):
        age = time.time() - os.path.getmtime(cache_file)
        if age < CONFIG["sp500_cache_ttl"]:
            logger.info("Using cached S&P 500 list")
            try:
                return pd.read_pickle(cache_file)
            except Exception as e:
                logger.warning(f"Load cache failed: {e}")

    try:
        logger.info("Fetching S&P 500 list from Wikipedia...")
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        df = pd.read_html(url, header=0)[0]
        try:
            df.to_pickle(cache_file)
        except Exception as e:
            logger.warning(f"Save cache failed: {e}")
        return df
    except Exception as e:
        logger.error(f"Failed to fetch S&P 500 list: {e}")
        if os.path.exists(cache_file):
            logger.info("Falling back to outdated cache")
            return pd.read_pickle(cache_file)
        raise

@lru_cache(maxsize=1024)
def match_to_sp500(name: str, df_key: str, thresh: int = None) -> str:
    if thresh is None:
        thresh = CONFIG["company_match_threshold"]
    df = get_sp500_list()
    companies = tuple(df["Security"].tolist())
    match, score, idx = process.extractOne(name, companies, scorer=fuzz.WRatio)
    return df.iloc[idx]["Symbol"] if score >= thresh else None
