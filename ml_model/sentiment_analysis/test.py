import json
import logging
from collections import defaultdict
from processing.analyzer import process_text_batch

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

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

    texts    = [item["text"] for item in example_batch]
    analyses = process_text_batch(texts)

    items = []
    for item, analysis in zip(example_batch, analyses):
        filtered = {
            "sentiment":     analysis["sentiment"],
            "sentiment_label": analysis["sentiment_label"],
            "realness":      analysis["realness"],
            "information":   analysis["information"],
            "overall_score": analysis["overall_score"],
            "ticker":        item["ticker"]
        }
        items.append({
            "input":    item,
            "analysis": filtered
        })

    date_ticker_scores = defaultdict(lambda: defaultdict(list))
    for entry in items:
        d = entry["input"]["date"]
        t = entry["analysis"]["ticker"]
        s = entry["analysis"]["sentiment"]
        date_ticker_scores[d][t].append(s)

    date_results = {}
    for date, tk_dict in date_ticker_scores.items():
        agg = {}
        for tkr, scores in tk_dict.items():
            avg = float(sum(scores) / len(scores))
            agg[tkr] = {"avg_score": avg}
        date_results[date] = agg

    output = {"items": items, "date_results": date_results}
    # print(json.dumps(output, ensure_ascii=False, indent=2))
    with open("analysis_full_output.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    logger.info("Full analysis written to analysis_full_output.json")
