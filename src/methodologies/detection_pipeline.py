"""Method 3: Detection-Guided Feedback Loop (v1.0 reference implementation).

Reference implementation of detector-in-the-loop rewriting. The detector
modules under `detectors/` are simplified educational versions, not the
full published research implementations. For production use, see the v1.5
Standard Pipeline (`src/standard/pipeline.py`).
"""

import re
from .detectors.binoculars import BinocularsDetector
from .detectors.roberta import RoBERTaDetector
from .detectors.statistical import StatisticalDetector
from .postprocess import PostProcessor


class DetectionGuidedProcessor:
    def __init__(self, config: dict):
        self.config = config.get("detection_guided", {})
        self.max_rounds = self.config.get("max_feedback_rounds", 2)
        self.threshold = self.config.get("threshold", 0.5)
        self.enable_gpu = self.config.get("enable_gpu", True)

        self.binoculars = BinocularsDetector(use_gpu=self.enable_gpu)
        self.roberta = RoBERTaDetector(use_gpu=self.enable_gpu)
        self.statistical = StatisticalDetector()
        self.postprocessor = PostProcessor(config)

    def _segment_sentences(self, text: str) -> list[str]:
        return [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]

    def _detect(self, text: str) -> float:
        scores = [
            self.binoculars.score(text),
            self.roberta.score(text),
            self.statistical.score(text),
        ]
        return sum(scores) / len(scores)

    def _rewrite_sentence(self, sentence: str) -> str:
        return self.postprocessor.process(sentence)

    def process(self, text: str, **kwargs) -> str:
        text = self.postprocessor.process(text)

        for _ in range(self.max_rounds):
            sentences = self._segment_sentences(text)
            flagged = []

            for i, sentence in enumerate(sentences):
                score = self._detect(sentence)
                if score > self.threshold:
                    flagged.append(i)

            if not flagged:
                break

            for i in flagged:
                sentences[i] = self._rewrite_sentence(sentences[i])

            text = " ".join(sentences)

        return text
