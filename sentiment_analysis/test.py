import logging
from batch_processor import process_news_batch

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    news1 = {
        "date": "2025-04-22",
        "text": "Tesla reports record first-quarter deliveries of 435,000 vehicles, beating analyst estimates and driving shares up 7% after hours."
    }
    long_paragraph = "Apple reported record iPhone sales in Greater China. " * 200
    news2 = {"date": "2025-04-21", "text": long_paragraph}
    news3 = {
        "date": "2025-04-20",
        "text": "Federal Reserve chair Jerome Powell indicates that interest rate cuts could be appropriate later this year if economic data supports easing."
    }
    news4 = {
        "date": "2025-04-19",
        "text": "Google unveils new AI-powered search features at its annual I/O conference, promising more personalized and context-aware results for users worldwide."
    }
    news5 = {
        "date": "2025-04-18",
        "text": "Amazon announces plans to open a new fulfillment center in Columbus, Ohio, creating over 2,500 full-time jobs ahead of the holiday shopping season."
    }
    news6 = {
        "date": "2025-04-17",
        "text": "BP reports a 15% decline in first-quarter profits due to rising operational costs and lower oil prices, although revenue exceeded analyst expectations."
    }

    example_batch = [news1, news2, news3, news4, news5, news6]
    logger.info("Starting example batch processing")
    result = process_news_batch(example_batch)
    logger.info(f"Overall sentiment score: {result['overall_score']}")
    logger.info(f"Per-company scores: {result['by_company']}")
    logger.info(
        f"{result['articles_processed']} articles processed, "
        f"{result['total_companies_matched']} companies matched"
    )
