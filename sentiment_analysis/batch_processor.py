import logging
import numpy as np
from collections import defaultdict
from data.sp500 import get_sp500_list, match_to_sp500
from processing.analyzer import process_text

logger = logging.getLogger(__name__)

def process_news_batch(news_batch: list[dict]) -> dict:
    logger.info(f"Processing batch of {len(news_batch)} news items")
    sp500_df = get_sp500_list()
    df_key = str(id(sp500_df))

    article_results = []
    for item in news_batch:
        text = item.get("text", "")
        if not text:
            continue
        res = process_text(text)
        res["date"] = item.get("date", "")
        article_results.append(res)

    if article_results:
        scores = [r["overall_score"] for r in article_results]
        infos = [r["information"] for r in article_results]
        reals = [r["realness"] for r in article_results]
        w_raw = np.array(infos) * np.array(reals)
        if w_raw.sum() > 0:
            w = w_raw / w_raw.sum()
            batch_score = float(np.dot(scores, w))
        else:
            batch_score = float(np.mean(scores))
    else:
        batch_score = 0.0

    company_scores = defaultdict(list)
    for art in article_results:
        for comp in art["companies"]:
            ticker = match_to_sp500(comp, df_key)
            if ticker:
                company_scores[ticker].append(art["overall_score"])

    by_company = {t: sum(v) / len(v) for t, v in company_scores.items()}

    return {
        "overall_score": batch_score,
        "by_company": by_company,
        "articles_processed": len(article_results),
        "total_companies_matched": len(by_company),
    }
