from common.infrastructure.mongodb.mongodb_client import MongoDbClient

from common.config.target_tickers import TARGET_TICKERS
from common.config.db_config import MONGODB_COLLECTION_NEWS, MONGODB_COLLECTION_SENTIMENT

mongo = MongoDbClient()
from datetime import date, timedelta
from types import SimpleNamespace




if __name__ == "__main__":
    sa_helper = SAHelper()
    
    # 确保你的 eod_callback 函数、sa_helper、MongoDbClient 等都在当前作用域中
    def eod_callback(msg):
        """
        当收到 EndOfDayEvent 时被调用
        event.date   -> datetime.date 对象
        event.source -> 发送源（例如 'unit_test'）
        """
        # 1. 提取日期，并转换成 YYYY-MM-DD 字符串
        date_str = msg.date.isoformat()
        print(f"[回调] 收到收盘事件：date={date_str}, source={msg.source}")

        # 2. 调用函数计算该日期下所有 ticker 的 avg_score
        scores = sa_helper.compute_avg_scores_for_date(date_str)

        # 3. 输出结果
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

        # 4. 打印最终结果
        print(sentiment_results)
        
        mongo = MongoDbClient()
        mongo.insert_many(MONGODB_COLLECTION_SENTIMENT, sentiment_results)

    start_date = date(1999, 1, 1)
    end_date   = date(2015, 12, 31)
    total_days = (end_date - start_date).days + 1

    for offset in range(total_days):
        current_date = start_date + timedelta(days=offset)
        # 构造一个与真实事件 msg 接口相同的对象
        fake_msg = SimpleNamespace(
            date=current_date,        # datetime.date 对象
            source='batch_run'        # 可自定义，日志里会打印出来
        )
        # 调用你的回调逻辑：计算、打标签、写入 MongoDB
        eod_callback(fake_msg)
