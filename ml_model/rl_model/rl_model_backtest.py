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