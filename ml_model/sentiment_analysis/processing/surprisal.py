import torch
from ml_model.sentiment_analysis.model_manager import ModelManager
from ml_model.sentiment_analysis.config import CONFIG

def calc_surprisal(text: str) -> float:
    tok = ModelManager.get_tokenizer("gpt2")
    mdl = ModelManager.get_model("gpt2")
    device = CONFIG["device"]

    max_len = tok.model_max_length - 10
    encoded = tok.encode(text)
    if len(encoded) > max_len:
        encoded = encoded[:max_len]
        text = tok.decode(encoded, skip_special_tokens=True)

    inputs = tok(text, return_tensors="pt").to(device)
    with torch.no_grad():
        outputs = mdl(**inputs, labels=inputs["input_ids"])

    return outputs.loss.item() * inputs["input_ids"].size(1)

def calc_surprisal_batch(texts: list[str]) -> list[float]:
    tok = ModelManager.get_tokenizer("gpt2")
    mdl = ModelManager.get_model("gpt2")
    device = CONFIG["device"]

    enc = tok(
        texts,
        return_tensors="pt",
        padding=True,
        truncation=True,
        max_length=tok.model_max_length - 10
    )
    input_ids      = enc["input_ids"].to(device)
    attention_mask = enc["attention_mask"].to(device)

    with torch.no_grad():
        outputs = mdl(input_ids, attention_mask=attention_mask, labels=input_ids)

    logits = outputs.logits
    shift_logits = logits[..., :-1, :].contiguous()
    shift_labels = input_ids[..., 1:].contiguous()
    shift_mask   = attention_mask[..., 1:].contiguous()

    loss_fct = torch.nn.CrossEntropyLoss(reduction="none")
    flat_loss = loss_fct(
        shift_logits.view(-1, shift_logits.size(-1)),
        shift_labels.view(-1)
    ).view(shift_labels.size())

    per_sample = (flat_loss * shift_mask).sum(dim=1).cpu().tolist()
    return per_sample
