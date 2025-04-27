import torch
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

def process_text_batch(texts: list[str], batch_size: int = 32) -> list[dict]:
    results: list[dict] = []
    for start in range(0, len(texts), batch_size):
        batch_texts = texts[start:start + batch_size]

        sent_logits = ModelManager.get_sentiment_logits(batch_texts)
        fake_logits = ModelManager.get_fake_news_logits(batch_texts)

        sent_probs = torch.softmax(sent_logits, dim=-1).cpu().numpy()
        fake_probs = torch.softmax(fake_logits, dim=-1).cpu().numpy()

        infos = ModelManager.calc_surprisal_batch(batch_texts)

        sent_pipe = ModelManager.get_model("sentiment")
        id2label = sent_pipe.model.config.id2label
        label2id = {label: idx for idx, label in id2label.items()}
        neg_idx = label2id.get("Negative", 0)
        neu_idx = label2id.get("Neutral", 1)
        pos_idx = label2id.get("Positive", 2)

        for idx, text in enumerate(batch_texts):
            p_neg = sent_probs[idx, neg_idx]
            p_neu = sent_probs[idx, neu_idx]
            p_pos = sent_probs[idx, pos_idx]

            if p_neu >= max(p_pos, p_neg):
                sent_score = 0.0
            else:
                sent_score = p_pos - p_neg

            real_score = fake_probs[idx, 1]
            info = infos[idx]

            max_idx = int(sent_probs[idx].argmax())
            label = id2label[max_idx]

            results.append({
                "text":            text,
                "sentiment":       float(sent_score),
                "realness":        float(real_score),
                "information":     float(info),
                "overall_score":   float(sent_score),
                "sentiment_label": label
            })
    return results
