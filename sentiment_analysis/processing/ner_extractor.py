import threading
from model_manager import ModelManager
from config import CONFIG

COMMON_NON_COMPANIES = {
    "The", "Government", "Ministry", "Department", "University", "School",
    "Committee", "Commission", "Agency", "Bureau", "Congress", "Senate",
    "Court", "Council", "Association", "Organization", "Foundation", "Institute"
}

_tokenizer_lock = threading.Lock()

def extract_companies(text: str) -> list[str]:
    ner = ModelManager.get_model("ner")
    tok = ner.tokenizer
    max_len = tok.model_max_length - 10

    encoded = tok.encode(text)
    if len(encoded) > max_len:
        text = tok.decode(encoded[:max_len], skip_special_tokens=True)

    ents = ner(text)
    companies = []
    for e in ents:
        if e["entity_group"] == "ORG":
            word = e["word"].strip()
            words = word.split()
            if (
                len(word) > 2
                and not any(w in COMMON_NON_COMPANIES for w in words)
                and not word.isupper()
            ):
                companies.append(word)
    return companies
