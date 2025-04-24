import torch
from model_manager import ModelManager
from config import CONFIG

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
