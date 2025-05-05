import time
import threading
from datetime import date
from typing import List, Tuple, Dict
from collections import defaultdict 

from common.config.target_tickers import TARGET_TICKERS
from common.config.db_config import MONGODB_COLLECTION_NEWS, MONGODB_COLLECTION_SENTIMENT
from common.config.kafka_config import KAFKA_SENTIMENT_ENDOFDAY_TOPIC
from common.model.end_of_day import EndOfDayEvent
from common.model.financial_news import FinancialNews
from common.model.sentiment_result import SentimentResult
from common.infrastructure.kafka.kafka_client import KafkaClient
from common.infrastructure.mongodb.mongodb_client import MongoDbClient
from ml_model.sentiment_analysis.analyzer import process_texts_smart_batch, ModelManager

tickers = TARGET_TICKERS

class SAHelper:
    def __init__(self):
        self.mongodb = MongoDbClient()
        self.kafka = KafkaClient()      
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
        analyses = process_texts_smart_batch(texts)

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
    
    def compute_avg_scores_for_date(
        self,
        date: str,
        zero_sent: float = 0.0
    ) -> Dict[str, float]:
        
        texts, metas = [], []
        for t in tickers:
            news_list = self.get_financial_news(t, date)
            if news_list:
                for news in news_list:
                    texts.append(f"{news.headline} {news.summary}")
                    metas.append(t)

        analyses = process_texts_smart_batch(texts) if texts else []

        scores_map = defaultdict(list)
        for t, a in zip(metas, analyses):
            scores_map[t].append((a["sentiment"], a["realness"], a["information"]))

        result: Dict[str, float] = {}
        for t in tickers:
            entries = scores_map.get(t, [])
            if not entries:
                result[t] = zero_sent
                continue

            s_list, r_list, i_list = zip(*entries)
            raw_w = [r * inf for r, inf in zip(r_list, i_list)]
            total_w = sum(raw_w) or 1.0
            norm_w = [w / total_w for w in raw_w]
            weighted_sent = sum(w * s for w, s in zip(norm_w, s_list))
            result[t] = weighted_sent

        return result
    
    def listen_end_of_day_for_sentiment(self, callback):
        self.kafka.listen(KAFKA_SENTIMENT_ENDOFDAY_TOPIC, callback)

    def send_end_of_day_to_sentiment(self, source="end_of_day_handler"):
        event = EndOfDayEvent(
            date=date.today(),
            source=source
        )

        self.kafka.send_message(KAFKA_SENTIMENT_ENDOFDAY_TOPIC, event)

    def eod_callback(self, record):
        try:
            payload = record.value
            date_str = payload["date"]

            scores = self.compute_avg_scores_for_date(date_str)

            sentiment_results = []
            for ticker, avg_score in scores.items():
                if avg_score == 0:
                    label = "Neutral"
                elif avg_score > 0:
                    label = "Positive"
                else:
                    label = "Negative"

                sentiment_results.append({
                    "ticker": ticker,
                    "avg_score": round(avg_score, 4),
                    "label": label,
                    "date": date_str
                })
            self.mongodb.delete(MONGODB_COLLECTION_SENTIMENT, {"date": date_str})
            self.mongodb.insert_many(MONGODB_COLLECTION_SENTIMENT, sentiment_results)
            print(f"[Callback] {date_str} | inserted {len(sentiment_results)} docs")

        except Exception as e:
            print(f"[Callback-Error] {e}")


if __name__ == "__main__":
    sa_helper = SAHelper()
    
    def eod_callback(record):
        try:
            payload = record.value            
            date_str = payload["date"]        

            scores = sa_helper.compute_avg_scores_for_date(date_str)

            sentiment_results = []
            for ticker, avg_score in scores.items():
                if avg_score == 0:
                    label = "Neutral"
                elif avg_score > 0:
                    label = "Positive"
                else:
                    label = "Negative"

                sentiment_results.append({
                    "ticker": ticker,
                    "avg_score": round(avg_score, 4),
                    "label": label,
                    "date": date_str
                })

            sa_helper.mongodb.insert_many(MONGODB_COLLECTION_SENTIMENT, sentiment_results)
            print(f"[Callback] {date_str} | inserted {len(sentiment_results)} docs")

        except Exception as e:
            print(f"[Callback-Error] {e}")
        
    def send_test_event():
        kafka = KafkaClient()
        time.sleep(1)

        evt = EndOfDayEvent(
            date=date.today(),
            source="unit_test"
        )
        print(f"[Sender] Sending event: {evt!r}")
        kafka.send_message(KAFKA_SENTIMENT_ENDOFDAY_TOPIC, evt)
    
    print("\SENTIMENT TEST ==================================")
    ticker = "NFLX"
    news = sa_helper.get_financial_news(ticker, "2012-10-30")
    labels, score = sa_helper.get_sentiment_analysis_result(ticker, "2012-10-30")
    for n, label in zip(news, labels):
        print(f"[News] {n}")
        print(f"[labls] {label}")
        
    print(f"[SENTIMENT SCORE FOR {ticker}] {score}")
        
    print("\nEndOfDay TEST ==================================")
    listener_thread = threading.Thread(
        target=lambda: sa_helper.listen_end_of_day_for_sentiment(eod_callback),
        daemon=True
    )
    listener_thread.start()

    sender_thread = threading.Thread(target=send_test_event)
    sender_thread.start()

    sender_thread.join()

    time.sleep(10)

    sa_helper.kafka.stop()
    print("Test complete.")