from typing import List, Tuple

from common.config.db_config import MONGODB_COLLECTION_NEWS
from common.model.financial_news import FinancialNews
from common.infrastructure.mongodb.mongodb_client import MongoDbClient
from ml_model.sentiment_analysis.processing.analyzer import process_text_batch, ModelManager

class SAHelper:
    def __init__(self):
        self.mongodb = MongoDbClient()      
        ModelManager.load_all_models()
        
    def get_financial_news(self, ticker: str, date: str) -> list[FinancialNews]:
        """
        Get financial news data from MongoDB
        :param ticker: stock code
        :param date: "YYYY-MM-DD" format date
        :return: list of financial news data
        """
        docs = self.mongodb.find(MONGODB_COLLECTION_NEWS, {"ticker": ticker, "date": date})

        if not docs:
            return []

        return [FinancialNews.from_raw(doc) for doc in docs]
        
    def get_sentiment_analysis_result(self, ticker: str, date: str) -> Tuple[List[str], float]:
        """
        Retrieve sentiment labels for each news item and compute the weighted average sentiment score for a given stock on a specific date.

        Args:
            ticker (str): Stock ticker symbol.
            date (str): Date in 'YYYY-MM-DD' format.

        Returns:
            Tuple[List[str], float]:
                - List of predicted sentiment labels for each news article.
                - Weighted average sentiment score for the date.
        """
        news_list = self.get_financial_news(ticker, date)
        if not news_list:
            # No news: return a single 'Neutral' label and a score of 0.0
            return ["Neutral"], 0.0

        # Concatenate headlines and summaries, then perform batch inference
        texts = [f"{item.headline}" for item in news_list]
        analyses = process_text_batch(texts)

        # Extract labels and metric values
        labels = [analysis.get("sentiment_label", "Neutral") for analysis in analyses]
        sentiments = [analysis.get("sentiment", 0.0) for analysis in analyses]
        realness = [analysis.get("realness", 0.0) for analysis in analyses]
        information = [analysis.get("information", 0.0) for analysis in analyses]

        # Compute raw weights as realness * information, then normalize
        raw_weights = [r * inf for r, inf in zip(realness, information)]
        total_weight = sum(raw_weights) or 1.0
        normalized_weights = [w / total_weight for w in raw_weights]

        # Calculate the weighted average sentiment score
        weighted_score = sum(w * s for w, s in zip(normalized_weights, sentiments))

        return labels, float(weighted_score)
    
if __name__ == "__main__":
    sa_helper = SAHelper()
    
    ticker = "NFLX"
    news = sa_helper.get_financial_news(ticker, "2011-10-30")
    labels, score = sa_helper.get_sentiment_analysis_result(ticker, "2011-10-30")
    for n, label in zip(news, labels):
        print(f"[News] {n}")
        print(f"[labls] {label}")

    print(f"[SENTIMENT SCORE FOR {ticker}] {score}")