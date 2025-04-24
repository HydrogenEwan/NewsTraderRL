import numpy as np
from concurrent.futures import ThreadPoolExecutor
from config import CONFIG
from model_manager import ModelManager
from processing.chunker import chunk_text
from processing.surprisal import calc_surprisal
from processing.ner_extractor import extract_companies

def process_chunk(chunk: str) -> dict:
    sent_pipe = ModelManager.get_model("sentiment")
    fake_pipe = ModelManager.get_model("fake_news")

    max_len = min(
        sent_pipe.tokenizer.model_max_length - 10,
        fake_pipe.tokenizer.model_max_length - 10,
    )
    tokens = sent_pipe.tokenizer.encode(chunk)
    if len(tokens) > max_len:
        chunk = sent_pipe.tokenizer.decode(tokens[:max_len], skip_special_tokens=True)

    res_f = sent_pipe(chunk)[0]
    if res_f["label"] == "Positive":
        sent_score = res_f["score"]
    elif res_f["label"] == "Negative":
        sent_score = -res_f["score"]
    else:
        sent_score = res_f["score"] * 0.2

    res_fake = fake_pipe(chunk)[0]
    real_score = res_fake["score"] if res_fake["label"] == "LABEL_1" else 1 - res_fake["score"]
    info_score = calc_surprisal(chunk)
    companies = extract_companies(chunk)

    return {
        "sentiment": float(sent_score),
        "realness": float(real_score),
        "information": float(info_score),
        "companies": companies,
        "text": chunk,
    }

def process_text(text: str) -> dict:
    chunks = chunk_text(text)
    with ThreadPoolExecutor(max_workers=CONFIG["max_workers"]) as ex:
        results = list(ex.map(process_chunk, chunks))

    sentiments = [r["sentiment"] for r in results]
    realness = [r["realness"] for r in results]
    information = [r["information"] for r in results]

    reals = np.array(realness)
    infos = np.array(information)
    weights_raw = reals * infos

    if weights_raw.sum() > 0:
        weights = weights_raw / weights_raw.sum()
        overall = float(np.dot(sentiments, weights))
    else:
        overall = float(np.mean(sentiments)) if sentiments else 0.0

    all_companies = [c for r in results for c in r["companies"]]

    return {
        "overall_score": overall,
        "sentiments": sentiments,
        "realness": float(np.mean(realness)) if realness else 0.5,
        "information": float(np.sum(information)),
        "companies": all_companies,
        "chunks": len(chunks),
    }
