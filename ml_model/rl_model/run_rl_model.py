import os
import sys
import logging
import threading
import time
from datetime import datetime

from ml_model.ml_model_helper import MlModelHelper
from ml_model.rl_model.rl_model_handler import RLModelHandler
from common.infrastructure.kafka.kafka_client import KafkaClient
from common.config.kafka_config import KAFKA_RL_ENDOFDAY_TOPIC
from common.model.end_of_day import EndOfDayEvent

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)

def main():
    logger = setup_logging()
    
    # Initialize ML model helper
    ml_helper = MlModelHelper()
    
    # Initialize RL model handler
    model_path = "ml_model/rl_model/trained_model_file/model_7dim_top20_output/model_file/final_model.pkl"  # Path to the trained model
    rl_handler = RLModelHandler(model_path)
    
    def end_of_day_callback(event):
        logger.info(f"Received end of day event: {event}")
        logger.info(f"[DEBUG] Raw event content: {event.__dict__}")
        try:
            rl_handler.process_end_of_day(event)
            logger.info("Successfully processed end of day event")
        except Exception as e:
            logger.error(f"Error processing end of day event: {str(e)}")
    
    # Create a thread for the Kafka listener
    listener_thread = threading.Thread(
        target=lambda: ml_helper.listen_end_of_day_for_rl(end_of_day_callback),
        daemon=True  # Make it a daemon thread so it will be terminated when main thread exits
    )
    
    # Start the listener thread
    logger.info("Starting Kafka listener thread...")
    listener_thread.start()
    
    # Keep the main thread running
    try:
        while True:
            # You can add other tasks here if needed
            pass
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        ml_helper.kafka.stop()
        # No need to join the listener thread since it's a daemon thread

if __name__ == "__main__":
    # Test RL model
    print("RL MODEL TEST ==================================")
    logger = setup_logging()
    
    # Initialize ML model helper
    ml_helper = MlModelHelper()
    
    # Initialize RL model handler
    model_path = "ml_model/rl_model/trained_model_file/model_7dim_top20_output/model_file/final_model.pkl"  # Path to the trained model
    rl_handler = RLModelHandler(model_path)
    
    def end_of_day_callback(event):
        logger.info(f"Received end of day event: {event}")
        logger.info(f"[DEBUG] Raw event content: {event.__dict__}")
        try:
            rl_handler.process_end_of_day(event)
            logger.info("Successfully processed end of day event")
        except Exception as e:
            logger.error(f"Error processing end of day event: {str(e)}")
    
    # Create a thread for the Kafka listener
    listener_thread = threading.Thread(
        target=lambda: ml_helper.listen_end_of_day_for_rl(end_of_day_callback),
        daemon=True  # Make it a daemon thread so it will be terminated when main thread exits
    )
    
    # Start the listener thread
    logger.info("Starting Kafka listener thread...")
    listener_thread.start()

    def send_test_event():
        kafka = KafkaClient()
        time.sleep(1)

        evt = EndOfDayEvent(
            date=datetime.now(),
            source="unit_test"
        )
        print(f"[Sender] Sending event: {evt!r}")
        kafka.send_message(KAFKA_RL_ENDOFDAY_TOPIC, evt)

    # Send test event
    sender_thread = threading.Thread(target=send_test_event)
    sender_thread.start()

    sender_thread.join()
    time.sleep(2)

    ml_helper.kafka.stop()
    print("Test complete.")