import json
import threading
from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import KafkaError
from common.config.kafka_config import KAFKA_BROKER, KAFKA_CONNECTOR_PREFIX


class KafkaClient:
    def __init__(self):
        self.bootstrap_servers = KAFKA_BROKER
        self.producers = {}
        self.consumers = {}
        self._stop_event = threading.Event()

    def listen(self, topic, callback, timeout_ms=1000, deserializer=None):
        # Default: JSON deserializer for object messages
        if topic not in self.consumers:
            if deserializer is None:
                deserializer = lambda b: json.loads(b.decode('utf-8'))

            self.consumers[topic] = KafkaConsumer(
                topic,
                bootstrap_servers=self.bootstrap_servers,
                auto_offset_reset='latest',
                value_deserializer=deserializer,
                enable_auto_commit=True,
                consumer_timeout_ms=None
            )

        consumer = self.consumers[topic]
        try:
            while not self._stop_event.is_set():
                records = consumer.poll(timeout_ms=timeout_ms)
                if not records:
                    continue
                for tp, msgs in records.items():
                    for msg in msgs:
                        try:
                            print(f"[INFO](KAFKA) Receiving message from topic {tp}")
                            callback(msg)
                        except Exception as e:
                            print(f"Error in callback: {e}")
        except KafkaError:
            print("KafkaConsumer encountered an error, shutting down listener")
        finally:
            consumer.close()

    def send_message(self, topic, message, serializer=None):
        # Default: JSON serializer for object messages, with to_dict support
        if topic not in self.producers:
            if serializer is None:
                def serializer(v):
                    try:
                        if hasattr(v, 'to_dict') and callable(v.to_dict):
                            v = v.to_dict()
                        return json.dumps(v).encode('utf-8')
                    except Exception as err:
                        print(f"Serializer error: {err}")
                        return str(v).encode('utf-8')

            self.producers[topic] = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=serializer
            )
        print(sending_message := f"[INFO](KAFKA) Sending message to topic {topic}: {message}")
        producer = self.producers[topic]
        future = producer.send(topic, value=message)
        try:
            future.get(timeout=10)
        except KafkaError as e:
            print(f"Failed to send message: {e}")

    def push_db(self, topic, obj):
        def db_serializer(v):
            header = topic.ljust(10)

            try:
                body = json.dumps(v)
            except (TypeError, ValueError) as err:
                print(f"Serializer error: {err}")
                body = str(v)
            return (header + body).encode('utf-8')

        self.send_message(KAFKA_CONNECTOR_PREFIX, obj, serializer=db_serializer)

    def listen_db(self, topic, callback, timeout_ms=1000):
        # For DB topics: parse fixed header and JSON body
        def wrapper(msg):
            value_str = msg.value  # decoded str
            # header is always fixed-length 'ohlc'
            header = value_str[:10].strip()
            body_str = value_str[10:]
            try:
                data = json.loads(body_str)
            except json.JSONDecodeError:
                print(f"Failed to decode JSON body {body_str}")
                data = {}
            callback(header, data)

        # Raw string deserializer
        deserializer = lambda b: b.decode('utf-8')
        self.listen(topic, wrapper, timeout_ms=timeout_ms, deserializer=deserializer)

    def stop(self):
        self._stop_event.set()
        for consumer in self.consumers.values():
            try:
                consumer.wakeup()
            except Exception:
                pass
        for p in self.producers.values():
            try:
                p.flush()
                p.close()
            except Exception as e:
                print(f"Error closing producer: {e}")
