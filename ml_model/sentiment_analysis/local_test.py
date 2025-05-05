import json
import logging
from collections import defaultdict

from common.config.target_tickers import TARGET_TICKERS
from ml_model.sentiment_analysis.analyzer import process_text_batch
from ml_model.ml_model_helper import MlModelHelper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

TEST_DATES = [
    "2011-10-30"
]

ZERO_SENT = 0

if __name__ == "__main__":
    helper = MlModelHelper()

    real_texts = []
    real_meta = []
    date_ticker_scores = defaultdict(lambda: defaultdict(list))

    for dt in TEST_DATES:
        for ticker in TARGET_TICKERS:
            news_list = helper.get_financial_news(ticker, dt)
            if news_list:
                for news in news_list:
                    txt = f"{news.headline} {news.summary}"
                    real_texts.append(txt)
                    real_meta.append((dt, ticker))
            else:
                date_ticker_scores[dt][ticker].append(ZERO_SENT)

    real_analyses = process_text_batch(real_texts) if real_texts else []
    date_ticker_metrics = defaultdict(lambda: defaultdict(list))

    for (dt, ticker), analysis in zip(real_meta, real_analyses):
        date_ticker_metrics[dt][ticker].append(
            (analysis["sentiment"], analysis["realness"], analysis["information"])
        )

    for dt in TEST_DATES:
        for ticker in TARGET_TICKERS:
            if ticker not in date_ticker_metrics[dt]:
                date_ticker_metrics[dt][ticker].append((0.0, 0.0, 0.0))

    date_results = {}
    for dt, tk_dict in date_ticker_metrics.items():
        date_results[dt] = {}
        for ticker, metrics in tk_dict.items():
            s_list, r_list, i_list = zip(*metrics)
            raw_w = [r * inf for r, inf in zip(r_list, i_list)]
            total_w = sum(raw_w) or 1.0
            norm_w = [w / total_w for w in raw_w]
            weighted_sent = sum(w * s for w, s in zip(norm_w, s_list))
            date_results[dt][ticker] = {"avg_score": float(weighted_sent)}

    with open("date_results.json", "w", encoding="utf-8") as f:
        json.dump(date_results, f, ensure_ascii=False, indent=2)
    logger.info("Weighted date results written to date_results.json")