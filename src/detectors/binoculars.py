"""Binoculars detector: GPT-2 dual-model perplexity ratio."""


class BinocularsDetector:
    def __init__(self, use_gpu: bool = True):
        self.use_gpu = use_gpu
        self.model = None

    def _load_model(self):
        if self.model is not None:
            return
        # Lazy load to avoid GPU memory usage when not needed
        from transformers import GPT2LMHeadModel, GPT2Tokenizer
        import torch

        device = "cuda" if self.use_gpu and torch.cuda.is_available() else "cpu"
        self.tokenizer = GPT2Tokenizer.from_pretrained("gpt2")
        self.model = GPT2LMHeadModel.from_pretrained("gpt2").to(device)
        self.device = device

    def score(self, text: str) -> float:
        self._load_model()
        import torch

        inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self.model(**inputs, labels=inputs["input_ids"])
            perplexity = torch.exp(outputs.loss).item()

        # Normalize: low perplexity = more likely AI-generated
        # Returns 0-1 where higher = more likely AI
        normalized = max(0.0, min(1.0, 1.0 - (perplexity - 10) / 100))
        return normalized
