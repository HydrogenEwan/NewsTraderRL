import torch
from collections import defaultdict
from ml_model.sentiment_analysis.model_manager import ModelManager

def split_text_chunks(texts: list[str], max_len: int = 512, overlap: int = 50) -> list[tuple[int, str]]:
    tokenizer = ModelManager.get_tokenizer("sentiment")
    chunk_data = []
    for idx, text in enumerate(texts):
        tokens = tokenizer.encode(text)
        start = 0
        while start < len(tokens):
            end = min(start + max_len, len(tokens))
            chunk_text = tokenizer.decode(tokens[start:end], skip_special_tokens=True)
            chunk_data.append((idx, chunk_text))
            if end == len(tokens):
                break
            start += max_len - overlap
    return chunk_data

def process_texts_smart_batch(texts: list[str], batch_size: int = 16) -> list[dict]:
    chunk_data = split_text_chunks(texts)
    results_by_idx = defaultdict(list)

    all_chunks = [chunk for _, chunk in chunk_data]
    chunk_indices = [idx for idx, _ in chunk_data]

    chunk_results = process_text_batch(all_chunks, batch_size)

    for idx, chunk_result in zip(chunk_indices, chunk_results):
        results_by_idx[idx].append(chunk_result)

    final_results = []
    for idx in range(len(texts)):
        chunks = results_by_idx[idx]
        sentiment = sum(r["sentiment"] for r in chunks) / len(chunks)
        realness = sum(r["realness"] for r in chunks) / len(chunks)
        information = sum(r["information"] for r in chunks) / len(chunks)

        final_results.append({
            "text": texts[idx],
            "sentiment": sentiment,
            "realness": realness,
            "information": information,
            "overall_score": sentiment,
        })

    return final_results


def process_text_batch(texts: list[str], batch_size: int = 32) -> list[dict]:
    results: list[dict] = []
    for start in range(0, len(texts), batch_size):
        batch = texts[start:start + batch_size]
        sent_probs = torch.softmax(
            ModelManager.get_sentiment_logits(batch), dim=-1
        ).cpu().numpy()
        fake_probs = torch.softmax(
            ModelManager.get_fake_news_logits(batch), dim=-1
        ).cpu().numpy()
        infos = ModelManager.calc_surprisal_batch(batch)

        for idx, text in enumerate(batch):
            neg, neu, pos = sent_probs[idx]
            sent_score = 0.0 if neu >= max(pos, neg) else (pos - neg)
            real_score = fake_probs[idx][1]

            results.append({
                "text":            text,
                "sentiment":       float(sent_score),
                "realness":        float(real_score),
                "information":     float(infos[idx]),
                "overall_score":   float(sent_score),
            })
    return results
