from ml_model.sentiment_analysis.model_manager import ModelManager
from ml_model.sentiment_analysis.config import CONFIG

def get_max_token_length() -> int:
    toks = [
        ModelManager.get_tokenizer("sentiment").model_max_length,
        ModelManager.get_tokenizer("fake_news").model_max_length,
        ModelManager.get_tokenizer("gpt2").model_max_length,
        ModelManager.get_tokenizer("ner").model_max_length,
    ]
    return min(toks)

def chunk_text(text: str) -> list[str]:
    tok = ModelManager.get_tokenizer("gpt2")
    max_len = get_max_token_length() - 50
    overlap = max(CONFIG["min_chunk_overlap"], int(max_len * CONFIG["chunk_overlap_ratio"]))
    encoded = tok.encode(text)
    if len(encoded) <= max_len:
        return [text]

    chunks = []
    start = 0
    while start < len(encoded):
        end = min(start + max_len, len(encoded))
        chunk_ids = encoded[start:end]
        chunks.append(tok.decode(chunk_ids, skip_special_tokens=True))
        start += max_len - overlap

    return chunks
