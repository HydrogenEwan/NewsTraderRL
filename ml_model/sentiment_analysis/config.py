import torch

CONFIG = {
    "device": 0 if torch.cuda.is_available() else -1,
    "chunk_overlap_ratio": 0.1,
    "min_chunk_overlap": 10,
    "max_workers": 4,
}