import logging
import torch
from transformers import pipeline, GPT2LMHeadModel, GPT2Tokenizer
from ml_model.sentiment_analysis.config import CONFIG

logger = logging.getLogger(__name__)

class ModelManager:
    _models = {}
    _tokenizers = {}

    @classmethod
    def load_all_models(cls):
        for name in ("sentiment", "fake_news", "gpt2", "ner"):
            if name not in cls._models:
                cls._load_model(name)
    
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
            pipe = pipeline(
                "sentiment-analysis",
                model=model_id,
                tokenizer=model_id,
                device=device
            )
            cls._models[name] = pipe
            cls._tokenizers[name] = pipe.tokenizer

        elif name == "fake_news":
            model_id = "mrm8488/bert-tiny-finetuned-fake-news-detection"
            pipe = pipeline(
                "text-classification",
                model=model_id,
                tokenizer=model_id,
                device=device
            )
            cls._models[name] = pipe
            cls._tokenizers[name] = pipe.tokenizer

        elif name == "gpt2":
            model_id = "gpt2"
            tok = GPT2Tokenizer.from_pretrained(model_id)
            tok.pad_token = tok.eos_token

            mdl = GPT2LMHeadModel.from_pretrained(model_id)
            mdl.to(device).eval()
            mdl.config.pad_token_id = mdl.config.eos_token_id

            cls._tokenizers[name] = tok
            cls._models[name] = mdl

        elif name == "ner":
            model_id = "dslim/bert-base-NER"
            pipe = pipeline(
                "ner",
                model=model_id,
                tokenizer=model_id,
                grouped_entities=True,
                device=device
            )
            cls._models[name] = pipe
            cls._tokenizers[name] = pipe.tokenizer

        else:
            raise ValueError(f"Unknown model name: {name}")

    @classmethod
    def get_sentiment_logits(cls, texts: list[str]) -> torch.Tensor:
        pipe = cls.get_model("sentiment")
        tokenizer = pipe.tokenizer
        model = pipe.model
        device = CONFIG["device"]

        enc = tokenizer(
            texts,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=512
        )
        inputs = {k: v.to(device) for k, v in enc.items()}
        with torch.no_grad():
            outputs = model(**inputs)
        return outputs.logits

    @classmethod
    def get_fake_news_logits(cls, texts: list[str]) -> torch.Tensor:
        pipe = cls.get_model("fake_news")
        tokenizer = pipe.tokenizer
        model = pipe.model
        device = CONFIG["device"]

        enc = tokenizer(
            texts,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=512
        )
        inputs = {k: v.to(device) for k, v in enc.items()}
        with torch.no_grad():
            outputs = model(**inputs)
        return outputs.logits
    
    @classmethod
    def calc_surprisal_batch(cls, texts: list[str]) -> list[float]:
        # get the raw tokenizer and model
        tok = cls.get_tokenizer("gpt2")
        mdl = cls.get_model("gpt2")
        device = CONFIG["device"]

        # tokenize with padding/truncation
        enc = tok(
            texts,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=tok.model_max_length - 10
        )
        input_ids      = enc["input_ids"].to(device)
        attention_mask = enc["attention_mask"].to(device)

        # forward with labels=input_ids to get per‐token loss
        with torch.no_grad():
            outputs = mdl(input_ids, attention_mask=attention_mask, labels=input_ids)

        logits = outputs.logits
        # shift for next‐token prediction
        shift_logits = logits[..., :-1, :].contiguous()
        shift_labels = input_ids[..., 1:].contiguous()
        shift_mask   = attention_mask[..., 1:].contiguous()

        # compute cross‐entropy without reduction
        loss_fct   = torch.nn.CrossEntropyLoss(reduction="none")
        flat_loss  = loss_fct(
            shift_logits.view(-1, shift_logits.size(-1)),
            shift_labels.view(-1)
        ).view(shift_labels.size())

        # sum over tokens for each sample
        surprisal = (flat_loss * shift_mask).sum(dim=1).cpu().tolist()
        return surprisal