"""RoBERTa-based AI text classifier."""


class RoBERTaDetector:
    def __init__(self, use_gpu: bool = True):
        self.use_gpu = use_gpu
        self.pipeline = None

    def _load_model(self):
        if self.pipeline is not None:
            return
        from transformers import pipeline
        import torch

        device = 0 if self.use_gpu and torch.cuda.is_available() else -1
        self.pipeline = pipeline(
            "text-classification",
            model="roberta-base-openai-detector",
            device=device,
        )

    def score(self, text: str) -> float:
        self._load_model()
        result = self.pipeline(text, truncation=True, max_length=512)[0]
        # "LABEL_0" = human, "LABEL_1" = AI (model-dependent)
        if result["label"] == "LABEL_1" or result["label"] == "Fake":
            return result["score"]
        return 1.0 - result["score"]
