import json
import threading
import unittest
from unittest.mock import patch, MagicMock
from datetime import date

from common.infrastructure.kafka.kafka_client import KafkaClient
from common.model.ohlc import Ohlc

class TestKafkaClientDbMethods(unittest.TestCase):
    def setUp(self):
        self.client = KafkaClient()
        self.topic = 'db-topic'
        # Sample Ohlc object
        self.sample = Ohlc(
            ticker='AAPL',
            date=date(2025, 4, 25),
            open=100.0,
            high=110.0,
            low=90.0,
            close=105.0,
            volume=1000
        )

    @patch('common.infrastructure.kafka.kafka_client.KafkaProducer')
    def test_push_db_serialization_and_send(self, mock_producer_cls):
        mock_producer = MagicMock()
        future = MagicMock()
        future.get.return_value = None
        mock_producer.send.return_value = future
        mock_producer_cls.return_value = mock_producer

        # Act
        self.client.push_db(self.topic, self.sample)

        # Assert producer created with custom serializer
        _, kwargs = mock_producer_cls.call_args
        serializer = kwargs['value_serializer']

        # Test serializer output
        header = 'ohlc'.ljust(10)
        body = json.dumps(self.sample.to_dict())
        expected_bytes = (header + body).encode('utf-8')
        self.assertEqual(serializer(self.sample), expected_bytes)

        # Ensure send called with original object
        mock_producer.send.assert_called_once_with(self.topic, value=self.sample)
        future.get.assert_called_once_with(timeout=10)

    @patch('common.infrastructure.kafka.kafka_client.KafkaConsumer')
    def test_listen_db_parsing(self, mock_consumer_cls):
        # Prepare raw message value (deserializer returns str)
        header = 'ohlc'.ljust(10)
        body = json.dumps(self.sample.to_dict())
        raw_str = (header + body)

        dummy_msg = MagicMock()
        dummy_msg.value = raw_str

        # Mock consumer.poll to return our dummy message then empty
        mock_consumer = MagicMock()
        mock_consumer.poll.side_effect = [
            {None: [dummy_msg]},
            {}
        ]
        mock_consumer_cls.return_value = mock_consumer

        received = []
        def callback(topic_label, data):
            received.append((topic_label, data))
            self.client.stop()

        listener_thread = threading.Thread(
            target=self.client.listen_db,
            args=(self.topic, callback, 100)
        )
        listener_thread.start()
        listener_thread.join(timeout=1)

        # Assertions
        self.assertEqual(received, [('ohlc', self.sample.to_dict())])
        mock_consumer.close.assert_called_once()

if __name__ == '__main__':
    unittest.main()
