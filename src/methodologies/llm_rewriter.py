"""Method 2: Multi-Turn LLM Rewriting (v1.0 reference implementation).

Reference implementation of iterative LLM rewriting with rhythm/vocabulary
prompts. For production use, the v1.5.1 Standard Pipeline integrates a
simpler, history-aware DeepSeek rewrite at translation boundaries — see
`src.standard.llm_rewriter`.
"""

import httpx


class LLMRewriteProcessor:
    """Multi-round LLM rewriter that varies sentence rhythm and vocabulary."""

    REWRITE_PROMPTS = [
        "Rewrite the following text with dramatically varied sentence lengths. "
        "Alternate between very short sentences (3-8 words) and longer complex ones (25-40 words). "
        "Use natural, conversational vocabulary. Preserve all factual content.",

        "Refine this text further: replace any formal or academic vocabulary with everyday equivalents. "
        "Add rhetorical questions or brief asides where they feel natural. "
        "Keep the meaning intact but make it sound like a knowledgeable person speaking casually.",

        "Final polish: ensure smooth transitions between sentences. "
        "Check that no three consecutive sentences have similar length. "
        "The text should feel genuinely human-written, not processed.",
    ]

    def __init__(self, config: dict):
        self.config = config.get("llm_rewrite", {})
        self.api_key = config.get("api_keys", {}).get("deepseek_api_key", "")
        self.model = self.config.get("model", "deepseek-chat")
        self.temperature = self.config.get("temperature", 1.2)
        self.top_p = self.config.get("top_p", 0.9)
        self.rounds = self.config.get("rounds", 2)

    def _call_llm(self, system_prompt: str, text: str) -> str:
        response = httpx.post(
            "https://api.deepseek.com/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text},
                ],
                "temperature": self.temperature,
                "top_p": self.top_p,
            },
            timeout=60,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

    def process(self, text: str, **kwargs) -> str:
        rounds = kwargs.get("rounds", self.rounds)
        current_text = text

        for i in range(min(rounds, len(self.REWRITE_PROMPTS))):
            current_text = self._call_llm(self.REWRITE_PROMPTS[i], current_text)

        return current_text
