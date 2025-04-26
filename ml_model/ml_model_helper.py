import time
import threading
from datetime import date

from common.config.db_config import MONGODB_COLLECTION_OHLC, MONGODB_COLLECTION_NEWS
from common.config.kafka_config import KAFKA_SENTIMENT_ENDOFDAY_TOPIC, KAFKA_RL_ENDOFDAY_TOPIC
from common.infrastructure.kafka.kafka_client import KafkaClient
from common.infrastructure.mongodb.mongodb_client import MongoDbClient
from common.model.end_of_day import EndOfDayEvent
from common.model.financial_news import FinancialNews
from common.model.ohlc import Ohlc


class MlModelHelper:
    def __init__(self):
        self.mongodb = MongoDbClient()
        self.kafka = KafkaClient()

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
    ohlc = ml_helper.get_ohlc("MMM", "2009-10-01")
    print(f"[OHLC] {ohlc}")
    print(f"[TURNOVER] {ml_helper.get_aggregate_turnover('2009-10-01')}")

    print("\nNEWS TEST ==================================")
    news = ml_helper.get_financial_news("UPS", "2009-12-30")
    for n in news:
        print(f"[News] {n}")

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