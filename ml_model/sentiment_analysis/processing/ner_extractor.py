# processing/ner_extractor.py

import threading
from model_manager import ModelManager
from config import CONFIG

COMMON_NON_COMPANIES = {
    "The", "Government", "Ministry", "Department", "University", "School",
    "Committee", "Commission", "Agency", "Bureau", "Congress", "Senate",
    "Court", "Council", "Association", "Organization", "Foundation", "Institute"
}

# 全局锁，保护 TokenizerFast 的任何 encode/decode/调用
_tokenizer_lock = threading.Lock()

def extract_companies(text: str) -> list[str]:
    """
    从文本中提取公司实体并过滤。整个 tokenize + pipeline 调用都在锁内，
    避免 TokenizerFast 在多线程中并发借用导致错误。
    """
    ner = ModelManager.get_model("ner")
    tok = ner.tokenizer
    max_len = tok.model_max_length - 10

    with _tokenizer_lock:
        # 先 encode 并截断
        encoded = tok.encode(text)
        if len(encoded) > max_len:
            encoded = encoded[:max_len]
            text = tok.decode(encoded, skip_special_tokens=True)
        # 再调用 pipeline（内部也会用 tokenizer）
        ents = ner(text)

    companies = []
    for e in ents:
        if e.get("entity_group") == "ORG":
            word = e.get("word", "").strip()
            words = word.split()
            if (
                len(word) > 2
                and not any(w in COMMON_NON_COMPANIES for w in words)
                and not word.isupper()
            ):
                companies.append(word)
    return companies
