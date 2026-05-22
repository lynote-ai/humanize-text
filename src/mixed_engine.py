"""Method 4: Mixed-Engine Translation."""

import re
from deep_translator import GoogleTranslator, MyMemoryTranslator


class MixedEngineProcessor:
    def __init__(self, config: dict):
        self.config = config.get("mixed_engine", {})
        self.engines = self.config.get("engines", ["google", "mymemory"])
        self.strategy = self.config.get("strategy", "best_score")

    def _get_translator(self, engine: str, source: str, target: str):
        if engine == "google":
            return GoogleTranslator(source=source, target=target)
        elif engine == "mymemory":
            return MyMemoryTranslator(source=source, target=target)
        raise ValueError(f"Unsupported engine: {engine}")

    def _segment(self, text: str) -> list[str]:
        return [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]

    def _score_naturalness(self, text: str) -> float:
        words = text.split()
        if not words:
            return 0.0
        unique_ratio = len(set(words)) / len(words)
        lengths = [len(w) for w in words]
        length_variance = sum((l - sum(lengths)/len(lengths))**2 for l in lengths) / len(lengths) if lengths else 0
        return unique_ratio * 0.6 + min(length_variance / 10, 0.4)

    def process(self, text: str, **kwargs) -> str:
        target_lang = "zh-CN"
        segments = self._segment(text)
        results = []

        for segment in segments:
            best_result = segment
            best_score = -1

            for engine_name in self.engines:
                try:
                    fwd = self._get_translator(engine_name, "en", target_lang)
                    translated = fwd.translate(segment)
                    bwd = self._get_translator(engine_name, target_lang, "en")
                    back_translated = bwd.translate(translated)
                    score = self._score_naturalness(back_translated)
                    if score > best_score:
                        best_score = score
                        best_result = back_translated
                except Exception:
                    continue

            results.append(best_result)

        return " ".join(results)
