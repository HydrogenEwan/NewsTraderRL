import torch
from collections import defaultdict
from ml_model.sentiment_analysis.model_manager import ModelManager
# from ml_model.sentiment_analysis.processing.chunker import chunk_text
# from ml_model.sentiment_analysis.processing.surprisal import calc_surprisal, calc_surprisal_batch

# def process_chunk(chunk: str) -> dict:
#     sent_pipe = ModelManager.get_model("sentiment")
#     fake_pipe = ModelManager.get_model("fake_news")

#     max_len = min(
#         sent_pipe.tokenizer.model_max_length - 10,
#         fake_pipe.tokenizer.model_max_length - 10,
#     )
#     tokens = sent_pipe.tokenizer.encode(chunk)
#     if len(tokens) > max_len:
#         chunk = sent_pipe.tokenizer.decode(tokens[:max_len], skip_special_tokens=True)

#     res_f = sent_pipe(chunk)[0]
#     if res_f["label"] == "Positive":
#         sent_score = res_f["score"]
#     elif res_f["label"] == "Negative":
#         sent_score = -res_f["score"]
#     else:
#         sent_score = 0

#     res_fake = fake_pipe(chunk)[0]
#     real_score = res_fake["score"] if res_fake["label"] == "LABEL_1" else 1 - res_fake["score"]
#     info_score = calc_surprisal(chunk)

#     return {
#         "sentiment": float(sent_score),
#         "realness": float(real_score),
#         "information": float(info_score),
#         "text": chunk,
#     }

# def process_text(text: str) -> dict:
#     chunks = chunk_text(text)
#     with ThreadPoolExecutor(max_workers=CONFIG["max_workers"]) as ex:
#         results = list(ex.map(process_chunk, chunks))

#     sentiments = [r["sentiment"] for r in results]
#     realness = [r["realness"] for r in results]
#     information = [r["information"] for r in results]

#     reals = np.array(realness)
#     infos = np.array(information)
#     weights_raw = reals * infos

#     if weights_raw.sum() > 0:
#         weights = weights_raw / weights_raw.sum()
#         overall = float(np.dot(sentiments, weights))
#     else:
#         overall = float(np.mean(sentiments)) if sentiments else 0.0

#     return {
#         "overall_score": overall,
#         "sentiments": sentiments,
#         "realness": float(np.mean(realness)) if realness else 0.5,
#         "information": float(np.sum(information)),
#         "chunks": len(chunks),
#     }

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

    # 统一批处理所有 chunks
    all_chunks = [chunk for _, chunk in chunk_data]
    chunk_indices = [idx for idx, _ in chunk_data]

    chunk_results = process_text_batch(all_chunks, batch_size)

    # 按原文本索引进行聚合
    for idx, chunk_result in zip(chunk_indices, chunk_results):
        results_by_idx[idx].append(chunk_result)

    # 聚合结果
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
        # 一次性获取 logits 并计算 softmax
        sent_probs = torch.softmax(
            ModelManager.get_sentiment_logits(batch), dim=-1
        ).cpu().numpy()
        fake_probs = torch.softmax(
            ModelManager.get_fake_news_logits(batch), dim=-1
        ).cpu().numpy()
        infos = ModelManager.calc_surprisal_batch(batch)

        for idx, text in enumerate(batch):
            neg, neu, pos = sent_probs[idx]
            # 如果中性概率最高，则得分 0，否则用正负之差
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
