import threading
from datetime import date, timedelta
from types import SimpleNamespace
from typing import List, Tuple, Dict, Optional
from collections import defaultdict 

from common.config.target_tickers import TARGET_TICKERS
from common.config.db_config import MONGODB_COLLECTION_NEWS, MONGODB_COLLECTION_SENTIMENT
from common.config.kafka_config import KAFKA_SENTIMENT_ENDOFDAY_TOPIC
from common.model.financial_news import FinancialNews
from common.model.sentiment_result import SentimentResult
from common.infrastructure.kafka.kafka_client import KafkaClient
from common.infrastructure.mongodb.mongodb_client import MongoDbClient
from ml_model.sentiment_analysis.processing.analyzer import process_texts_smart_batch, ModelManager

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

    def listen_end_of_day_for_sentiment(
        self,
        callback,
        test_input: Optional[str] = None
    ):
        if test_input:
            from common.model.end_of_day import EndOfDayEvent
            import datetime

            evt_literal = test_input.split("Sending event: ")[1]

            namespace = {
                "EndOfDayEvent": EndOfDayEvent,
                "datetime": datetime
            }
            event = eval(evt_literal, namespace)

            callback(event)
        else:
            self.kafka.listen(KAFKA_SENTIMENT_ENDOFDAY_TOPIC, callback)

    
if __name__ == "__main__":
    sa_helper = SAHelper()
    
    def eod_callback(msg):
        """
        Called when an EndOfDayEvent is received.
        event.date   -> datetime.date object
        event.source -> source of the event (e.g., 'unit_test')
        """
        # 1. Extract the date and convert to a YYYY-MM-DD string
        date_str = msg.date.isoformat()
        print(f"[Callback] Received end-of-day event: date={date_str}, source={msg.source}")

        # 2. Compute the average score for each ticker on that date
        scores = sa_helper.compute_avg_scores_for_date(date_str)

        # 3. Build the list of sentiment results
        sentiment_results = []
        for ticker, avg_score in scores.items():
            if avg_score == 0.0:
                label = "Neutral"
            elif avg_score > 0:
                label = "Positive"
            else:
                label = "Negative"

            result = SentimentResult(
                ticker=ticker,
                avg_score=round(avg_score, 4),
                label=label,
                date=date_str
            )
            sentiment_results.append(result.to_dict())

        # 4. (Optional) Uncomment the following line to print the final results
        # print(sentiment_results)
        
        # 5. Insert the sentiment results into MongoDB
        mongo = MongoDbClient()
        mongo.insert_many(MONGODB_COLLECTION_SENTIMENT, sentiment_results)
    
    # print("\SENTIMENT TEST ==================================")
    # ticker = "NFLX"
    # news = sa_helper.get_financial_news(ticker, "2012-10-30")
    # labels, score = sa_helper.get_sentiment_analysis_result(ticker, "2012-10-30")
    # for n, label in zip(news, labels):
    #     print(f"[News] {n}")
    #     print(f"[labls] {label}")
        
    # print(f"[SENTIMENT SCORE FOR {ticker}] {score}")
        
    # print("\nEndOfDay TEST ==================================")
    # listener_thread = threading.Thread(
    #     target=lambda: sa_helper.listen_end_of_day_for_sentiment(
    #         eod_callback,
    #         test_input="[Sender] Sending event: EndOfDayEvent(date=datetime.date(2012, 4, 28), source='unit_test')"
    #     ),
    #     daemon=False
    # )
    # listener_thread.start()
    
    start_date = date(2006, 3, 30)
    end_date   = date(2015, 12, 31)
    total_days = (end_date - start_date).days + 1

    for offset in range(total_days):
        current_date = start_date + timedelta(days=offset)
        fake_msg = SimpleNamespace(
            date=current_date,    
            source='batch_run'   
        )
        eod_callback(fake_msg)
