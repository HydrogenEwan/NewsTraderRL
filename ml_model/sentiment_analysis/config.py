import torch

CONFIG = {
    "device": 0 if torch.cuda.is_available() else -1,
    "sp500_cache_file": "sp500_cache.pkl",
    "sp500_cache_ttl": 24 * 60 * 60,
    "company_match_threshold": 80,
    "chunk_overlap_ratio": 0.1,
    "min_chunk_overlap": 10,
    "max_workers": 4,
}