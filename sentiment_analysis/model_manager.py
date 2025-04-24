import logging
from transformers import pipeline, GPT2LMHeadModel, GPT2Tokenizer
from config import CONFIG

logger = logging.getLogger(__name__)

class ModelManager:
    _models = {}
    _tokenizers = {}

    @classmethod
    def get_model(cls, name: str):
        if name not in cls._models:
            cls._load_model(name)
        return cls._models[name]

    @classmethod
    def get_tokenizer(cls, name: str):
        if name not in cls._tokenizers:
            cls._load_model(name)
        return cls._tokenizers[name]

    @classmethod
    def _load_model(cls, name: str):
        device = CONFIG["device"]
        if name == "sentiment":
            model_id = "yiyanghkust/finbert-tone"
            pipe = pipeline("sentiment-analysis", model=model_id, tokenizer=model_id, device=device)
            cls._models[name] = pipe
            cls._tokenizers[name] = pipe.tokenizer

        elif name == "fake_news":
            model_id = "mrm8488/bert-tiny-finetuned-fake-news-detection"
            pipe = pipeline("text-classification", model=model_id, tokenizer=model_id, device=device)
            cls._models[name] = pipe
            cls._tokenizers[name] = pipe.tokenizer

        elif name == "gpt2":
            model_id = "gpt2"
            tok = GPT2Tokenizer.from_pretrained(model_id)
            mdl = GPT2LMHeadModel.from_pretrained(model_id).to(device).eval()
            cls._tokenizers[name] = tok
            cls._models[name] = mdl

        elif name == "ner":
            model_id = "dslim/bert-base-NER"
            pipe = pipeline("ner", model=model_id, tokenizer=model_id, grouped_entities=True, device=device)
            cls._models[name] = pipe
            cls._tokenizers[name] = pipe.tokenizer

        else:
            raise ValueError(f"Unknown model name: {name}")
