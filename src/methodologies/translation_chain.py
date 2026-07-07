"""Method 1: Multi-Language Translation Chain (v1.0 reference implementation).

This is one of the four original methodologies. For production use, the v1.5
Standard Pipeline (`src/standard/pipeline.py`) integrates this method with
Method 2 (LLM Rewriting) into a fixed, validated 4-step chain.
"""

from deep_translator import GoogleTranslator, MyMemoryTranslator


class TranslationChainProcessor:
    TIERS = {
        "standard": 3,
        "advanced": 4,
        "focus": 5,
    }

    def __init__(self, config: dict):
        self.config = config.get("translation_chain", {})
        # Use locale-aware codes so both Google and MyMemory accept them.
        self.chain = self.config.get("chain", ["zh-CN", "ja-JP", "fi"])
        self.engines = self.config.get("engines", ["google", "mymemory"])

    @staticmethod
    def _normalize_language(engine: str, code: str) -> str:
        """Map user/language codes to the format each engine expects."""
        low = code.lower()
        if engine == "mymemory":
            if low.startswith("ja"):
                return "ja-JP"
            if low == "en":
                return "en-US"
            return code
        elif engine == "google":
            # Google only supports a few locale tags; strip regions for the rest.
            if low in {"zh-cn", "zh-tw", "mni-mtei"}:
                return code
            return code.split("-")[0]
        return code

    def _get_translator(self, engine: str, source: str, target: str):
        source = self._normalize_language(engine, source)
        target = self._normalize_language(engine, target)
        if engine == "google":
            return GoogleTranslator(source=source, target=target)
        elif engine == "mymemory":
            return MyMemoryTranslator(source=source, target=target)
        raise ValueError(f"Unsupported engine: {engine}")

    def process(self, text: str, tier: str = "standard", language: str = "en", **kwargs) -> str:
        max_hops = self.TIERS.get(tier, 3)
        languages = self.chain[:max_hops - 1]
        current_text = text
        prev_lang = language

        for i, lang in enumerate(languages):
            engine = self.engines[i % len(self.engines)]
            translator = self._get_translator(engine, prev_lang, lang)
            current_text = translator.translate(current_text)
            prev_lang = lang

        final_translator = self._get_translator(self.engines[0], prev_lang, language)
        current_text = final_translator.translate(current_text)

        return current_text
