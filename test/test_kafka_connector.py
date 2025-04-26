from __future__ import annotations
import json
import time
from dataclasses import dataclass
from typing import Any

from kafka import KafkaProducer
from pymongo import MongoClient

from common.config.db_config import MONGODB_URI


# --- Ohlc 정의 (common/model/daily_basis_model 내부 상속 가정) ---
@dataclass
class Ohlc:
    ticker: str
    date: str   # ISO 포맷 문자열
    open: float
    high: float
    low: float
    close: float
    volume: int

    def to_dict(self) -> dict:
        return {
            "ticker": self.ticker,
            "date": self.date,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume
        }

# --- 설정 ---
KAFKA_BROKERS = ["seongjaeny.com:9092"]
KAFKA_TOPIC   = "kafka_ohlc_test"

MONGO_URI     = MONGODB_URI
MONGO_DB      = "newstraderrl"
MONGO_COLL    = "kafka_ohlc_test"

def produce_test_message():
    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BROKERS,
        value_serializer=lambda v: json.dumps(v).encode("utf-8")
    )


    sample = Ohlc(
        ticker="AAPL",
        date="2025-04-24",
        open=172.5,
        high=174.0,
        low=171.8,
        close=173.6,
        volume=25_000_000
    )

    try:
        future = producer.send(KAFKA_TOPIC, sample.to_dict())
        result = future.get(timeout=5)
        print("✔️ Sent successfully:", result)
    except Exception as e:
        print("❌ Kafka send failed:", e)

    print(">>> Sending to Kafka:", sample)
    producer.send(KAFKA_TOPIC, sample.to_dict())
    producer.flush()
    producer.close()

def verify_in_mongo(timeout: int = 10):
    client = MongoClient(MONGO_URI)
    coll = client[MONGO_DB][MONGO_COLL]

    print(f">>> Waiting up to {timeout}s for document in MongoDB...")
    for i in range(timeout):
        doc = coll.find_one({"ticker": "AAPL", "date": "2025-04-24"})
        if doc:
            print("✅ Found in MongoDB:", doc)
            return
        time.sleep(1)
    print("⚠️ Timeout: 문서를 찾을 수 없습니다.")

if __name__ == "__main__":
    # 1) Kafka로 보내기
    produce_test_message()

    # 2) 잠시 대기 후 MongoDB 확인
    verify_in_mongo()
