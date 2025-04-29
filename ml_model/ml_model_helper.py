import time
import threading
from datetime import date
from typing import List, Tuple

from common.config.db_config import MONGODB_COLLECTION_OHLC, MONGODB_COLLECTION_NEWS
from common.config.kafka_config import KAFKA_SENTIMENT_ENDOFDAY_TOPIC, KAFKA_RL_ENDOFDAY_TOPIC
from common.infrastructure.kafka.kafka_client import KafkaClient
from common.infrastructure.mongodb.mongodb_client import MongoDbClient
from common.model.end_of_day import EndOfDayEvent
from common.model.financial_news import FinancialNews
from common.model.ohlc import Ohlc

from ml_model.sentiment_analysis.processing.analyzer import process_text_batch, ModelManager


class MlModelHelper:
    def __init__(self):
        self.mongodb = MongoDbClient()
        self.kafka = KafkaClient()
        
        ModelManager.load_all_models()

    def get_ohlc(self, ticker: str, date: str) -> Ohlc:
        """
        Get OHLC data from MongoDB
        :param ticker: stock code
        :param date: "YYYY-MM-DD" format date
        :return: OHLC data
        """
        docs = self.mongodb.find(MONGODB_COLLECTION_OHLC, {"ticker": ticker, "date": date})

        if not docs:
            return None

        for doc in docs:
            return Ohlc.from_raw(doc)

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
        texts = [f"{item.headline} {item.summary}" for item in news_list]
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

    # def get_sec(self, ticker: str, date: str) -> list[dict]:
    #     docs = self.mongodb.find(MONGODB_COLLECTION_OHLC, {"ticker": ticker})
    #
    #     if not docs:
    #         return None
    #
    #     for doc in docs:
    #         return doc.get("sec", None)

    def get_aggregate_turnover(self, date: str) -> float:
        client = self.mongodb
        pipeline = [
            {"$match": {"date": date}},
            {"$group": {"_id": None, "turnover": {"$sum": {"$multiply": ["$volume", "$close"]}}}},
            {"$project": {"_id": 0, "turnover": 1}}
        ]
        result = client.aggregate("ohlc", pipeline)
        if result and len(result) > 0:
            # 첫 번째 문서의 turnover 값을 반환
            return float(result[0].get("turnover", 0.0))
        return 0.0

    def listen_end_of_day_for_sentiment(self, callback):
        self.kafka.listen(KAFKA_SENTIMENT_ENDOFDAY_TOPIC, callback)

    def listen_end_of_day_for_rl(self, callback):
        self.kafka.listen(KAFKA_RL_ENDOFDAY_TOPIC, callback)

    def send_end_of_day_to_rl(self, source="sentiment"):
        event = EndOfDayEvent(
            date=date.today(),
            source=source
        )

        self.kafka.send_message(KAFKA_RL_ENDOFDAY_TOPIC, event)


if __name__ == "__main__":
    def example_callback(msg):
        print(f"[Listener] Received message: {msg}")


    def send_test_event():
        kafka = KafkaClient()
        time.sleep(1)

        evt = EndOfDayEvent(
            date=date.today(),
            source="unit_test"
        )
        print(f"[Sender] Sending event: {evt!r}")
        kafka.send_message(KAFKA_SENTIMENT_ENDOFDAY_TOPIC, evt)

    ml_helper = MlModelHelper()

    print("OHLC TEST ==================================")
    ohlc = ml_helper.get_ohlc("^GSPC", "1999-01-04")
    print(f"[OHLC] {ohlc}")
    print(f"[TURNOVER] {ml_helper.get_aggregate_turnover('2009-10-01')}")

    start = time.perf_counter()

    print("\nNEWS TEST ==================================")
    ticker = "DUK"
    news = ml_helper.get_financial_news(ticker, "2015-12-30")
    labels, score = ml_helper.get_sentiment_analysis_result(ticker, "2015-12-30")
    for n, label in zip(news, labels):
        print(f"[News] {n}")
        print(f"[labls] {label}")

    print(f"[SENTIMENT SCORE FOR {ticker}] {score}")

    end = time.perf_counter()
    print(f"Elapsed time: {end - start:.3f} seconds")
            

    print("\nEndOfDay TEST ==================================")
    listener_thread = threading.Thread(
        target=lambda: ml_helper.listen_end_of_day_for_sentiment(example_callback),
        daemon=True
    )
    listener_thread.start()

    sender_thread = threading.Thread(target=send_test_event)
    sender_thread.start()

    sender_thread.join()

    time.sleep(2)

    ml_helper.kafka.stop()
    print("Test complete.")