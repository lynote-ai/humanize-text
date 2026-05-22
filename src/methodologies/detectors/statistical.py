"""Statistical feature-based AI text detection."""

import re
import math


class StatisticalDetector:
    def score(self, text: str) -> float:
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]
        if len(sentences) < 2:
            return 0.5

        words = text.split()
        if not words:
            return 0.5

        # Type-Token Ratio (lower = more repetitive = more AI-like)
        ttr = len(set(w.lower() for w in words)) / len(words)

        # Sentence length variance (lower = more uniform = more AI-like)
        lengths = [len(s.split()) for s in sentences]
        mean_len = sum(lengths) / len(lengths)
        variance = sum((l - mean_len) ** 2 for l in lengths) / len(lengths)
        std_dev = math.sqrt(variance)
        cv = std_dev / mean_len if mean_len > 0 else 0

        # Hapax legomena ratio (words appearing only once)
        word_counts = {}
        for w in words:
            w_lower = w.lower()
            word_counts[w_lower] = word_counts.get(w_lower, 0) + 1
        hapax_ratio = sum(1 for c in word_counts.values() if c == 1) / len(word_counts) if word_counts else 0

        # Combine signals: low TTR + low CV + low hapax = likely AI
        ttr_score = max(0, min(1, (0.7 - ttr) / 0.3))
        cv_score = max(0, min(1, (0.5 - cv) / 0.3))
        hapax_score = max(0, min(1, (0.6 - hapax_ratio) / 0.3))

        return (ttr_score + cv_score + hapax_score) / 3
