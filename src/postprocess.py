"""Post-processing: AI vocabulary replacement and sentence rhythm disruption."""

import random
import re

AI_VOCAB_REPLACEMENTS = {
    "utilize": ["use", "apply", "work with"],
    "facilitate": ["help", "support", "enable"],
    "comprehensive": ["full", "complete", "thorough"],
    "subsequently": ["then", "after that", "next"],
    "furthermore": ["also", "plus", "on top of that"],
    "demonstrate": ["show", "prove", "illustrate"],
    "implement": ["build", "set up", "put in place"],
    "leverage": ["use", "take advantage of", "tap into"],
    "optimize": ["improve", "fine-tune", "make better"],
    "paradigm": ["model", "approach", "framework"],
    "synergy": ["teamwork", "combined effect", "collaboration"],
    "methodology": ["method", "approach", "process"],
    "innovative": ["new", "creative", "fresh"],
    "streamline": ["simplify", "speed up", "smooth out"],
    "unprecedented": ["never seen before", "unheard of", "groundbreaking"],
    "transformative": ["game-changing", "revolutionary", "major"],
    "ecosystem": ["environment", "landscape", "space"],
    "scalable": ["flexible", "expandable", "growable"],
    "robust": ["strong", "solid", "reliable"],
    "cutting-edge": ["latest", "advanced", "modern"],
    "delve": ["dig into", "explore", "look at"],
    "intricate": ["complex", "detailed", "involved"],
    "pivotal": ["key", "crucial", "central"],
    "encompasses": ["includes", "covers", "spans"],
    "multifaceted": ["complex", "varied", "diverse"],
    "realm": ["area", "field", "world"],
    "commendable": ["impressive", "notable", "praiseworthy"],
    "meticulous": ["careful", "thorough", "precise"],
    "paramount": ["essential", "critical", "top priority"],
    "underscore": ["highlight", "stress", "emphasize"],
}


class PostProcessor:
    def __init__(self, config: dict):
        pp_config = config.get("postprocess", {})
        self.replace_vocab = pp_config.get("replace_ai_vocab", True)
        self.disrupt_rhythm = pp_config.get("disrupt_rhythm", True)
        self.short_threshold = pp_config.get("short_sentence_threshold", 8)

    def _replace_ai_vocabulary(self, text: str) -> str:
        for word, replacements in AI_VOCAB_REPLACEMENTS.items():
            pattern = re.compile(re.escape(word), re.IGNORECASE)
            if pattern.search(text):
                replacement = random.choice(replacements)
                text = pattern.sub(replacement, text, count=1)
        return text

    def _disrupt_sentence_rhythm(self, text: str) -> str:
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]
        if len(sentences) < 3:
            return text

        result = []
        i = 0
        while i < len(sentences):
            words_current = len(sentences[i].split())
            if (i + 1 < len(sentences)
                    and words_current < self.short_threshold
                    and len(sentences[i + 1].split()) < self.short_threshold):
                merged = sentences[i].rstrip('.!?') + " — " + sentences[i + 1][0].lower() + sentences[i + 1][1:]
                result.append(merged)
                i += 2
            else:
                result.append(sentences[i])
                i += 1

        return " ".join(result)

    def process(self, text: str) -> str:
        if self.replace_vocab:
            text = self._replace_ai_vocabulary(text)
        if self.disrupt_rhythm:
            text = self._disrupt_sentence_rhythm(text)
        return text
