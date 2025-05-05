import os
import sys
import logging
import threading
import time
from datetime import datetime

import torch
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from collections import defaultdict

from ml_model.ml_model_helper import MlModelHelper
from ml_model.rl_model.rl_model_handler import RLModelHandler
from ml_model.ml_model_helper import MlModelHelper
from common.infrastructure.kafka.kafka_client import KafkaClient
from common.config.kafka_config import KAFKA_RL_ENDOFDAY_TOPIC
from common.model.end_of_day import EndOfDayEvent
from common.config.target_tickers import TARGET_TICKERS
from datetime import date, timedelta

rl_handler = RLModelHandler(model_path="ml_model/rl_model/trained_model_file/model_7dim_top20_output/model_file/best_cr-34.pth")
ml_helper = MlModelHelper()

start_date = date(2005, 1, 1)
end_date = date(2015, 1, 1)

current_date = start_date

prev_weights = np.ones(len(TARGET_TICKERS)) / len(TARGET_TICKERS)
portfolio_amount = 100

stocks_data, _ = rl_handler._fetch_data_from_mongodb(start_date.strftime("%Y-%m-%d"))
prev_prices = stocks_data[:, -1, 0]

#Add initial values
dates, returns, history_weights = [], [], []

while current_date <= end_date:
        # record dates
        dates.append(current_date.strftime('%Y-%m'))

        # get RL weights
        event             = EndOfDayEvent(date=current_date, source="backtest")
        result            = rl_handler.process_end_of_day(event)
        rl_weights        = np.array(result.to_dict()['portfolio_weights'][:len(TARGET_TICKERS)])

        # zero out weights for dead tickers, then renormalize
        mask   = prev_prices > 0
        w_live = rl_weights.copy()
        w_live[~mask] = 0
        w_live /= w_live.sum()

        # record weights
        history_weights.append(w_live)

        # compute allocation and shares
        alloc = portfolio_amount * w_live
        with np.errstate(divide='ignore', invalid='ignore'):
            shares = np.where(prev_prices > 0, alloc / prev_prices, 0.0)

        # fetch this month-end prices
        stocks_data, _ = rl_handler._fetch_data_from_mongodb(current_date.strftime("%Y-%m-%d"))
        prices = stocks_data[:, -1, 0]

        # compute new portfolio value & return
        new_val = (shares * prices).sum()
        r = (new_val - portfolio_amount) / portfolio_amount
        returns.append(r)

        # update for next loop
        portfolio_amount = new_val
        prev_prices      = prices

        print(f"{current_date.strftime('%Y-%m')} | Return: {r:.2f} | Amount: {new_val:.2f}")

        # next month
        if current_date.month == 12:
            current_date = date(current_date.year + 1, 1, 1)
        else:
            current_date = date(current_date.year, current_date.month + 1, 1)


print(f"returns: {returns}")
print(f"portfolio_amount: {portfolio_amount}")

# Plot cumulative returns
cumulative_returns = np.cumprod([1 + r for r in returns])
plt.figure(figsize=(10, 5))
plt.plot(dates, cumulative_returns)
plt.title("Cumulative Return")
plt.xticks(rotation=45)
plt.grid(True)
plt.tight_layout()
plt.show()

# Plot heatmap of portfolio weights
portfolio_df = pd.DataFrame(history_weights, columns=TARGET_TICKERS, index=dates)
plt.figure(figsize=(12, 8))
plt.imshow(portfolio_df.T, aspect='auto', interpolation='nearest', cmap='viridis')
plt.colorbar(label='Weight')
plt.title("Portfolio Allocation Heatmap")
plt.xlabel("Time (Month)")
plt.ylabel("Asset")
plt.xticks(ticks=np.linspace(0, len(dates)-1, 10), labels=np.array(dates)[::len(dates)//10], rotation=45)
plt.yticks(ticks=np.arange(len(TARGET_TICKERS)), labels=TARGET_TICKERS)
plt.tight_layout()
plt.show()