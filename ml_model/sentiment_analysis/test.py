
import json
import logging
from collections import defaultdict
from processing.analyzer import process_text

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def score_to_label(score: float) -> str:
    if score > 0:
        return "Positive"
    elif score < 0:
        return "Negative"
    else:
        return "Neutral"

if __name__ == "__main__":
    example_batch = [
        {
            "date": "2025-04-20",
            "ticker": "TSLA",
            "text": "Tesla reports record first-quarter deliveries of 435,000 vehicles, beating analyst estimates and driving shares up 7% after hours."
        },
        {
            "date": "2025-04-23",
            "ticker": "AAPL",
            "text": "Apple reported record iPhone sales in Greater China."
        },
        {
            "date": "2025-04-19",
            "ticker": "FED",
            "text": "Federal Reserve chair Jerome Powell indicates that interest rate cuts could be appropriate later this year if economic data supports easing."
        },
        {
            "date": "2025-04-19",
            "ticker": "GOOGL",
            "text": "Google unveils new AI-powered search features at its annual I/O conference, promising more personalized and context-aware results for users worldwide."
        },
        {
            "date": "2025-04-19",
            "ticker": "AMZN",
            "text": "Amazon announces plans to open a new fulfillment center in Columbus, Ohio, creating over 2,500 full-time jobs ahead of the holiday shopping season."
        },
        {
            "date": "2025-04-19",
            "ticker": "BP",
            "text": "BP reports a 15% decline in first-quarter profits due to rising operational costs and lower oil prices, although revenue exceeded analyst expectations."
        },
    ]

    # 先对每条新闻做分析
    records = []
    for item in example_batch:
        analysis = process_text(item["text"])
        score = analysis["overall_score"]
        records.append({
            "date": item["date"],
            "ticker": item["ticker"],
            "score": score
        })

    # 按 date -> ticker 收集分数列表
    date_ticker_scores = defaultdict(lambda: defaultdict(list))
    for rec in records:
        date_ticker_scores[rec["date"]][rec["ticker"]].append(rec["score"])

    # 计算 avg_score 和 label
    date_results = {}
    for date, tk_dict in date_ticker_scores.items():
        agg = {}
        for tkr, scores in tk_dict.items():
            avg = sum(scores) / len(scores)
            agg[tkr] = {
                "avg_score": avg,
                "label": score_to_label(avg)
            }
        date_results[date] = agg

    # 写到本地 JSON
    with open("analysis_by_date.json", "w", encoding="utf-8") as f:
        json.dump({"date_results": date_results}, f, ensure_ascii=False, indent=2)

    # 控制台输出
    print(json.dumps({"date_results": date_results}, ensure_ascii=False, indent=2))
    logger.info("Date-level analysis written to analysis_by_date.json")