"""Method 2: Multi-Turn LLM Rewriting (v1.0 reference implementation).

Reference implementation of iterative LLM rewriting with rhythm/vocabulary
prompts. For production use, the v1.5.1 Standard Pipeline integrates a
simpler, history-aware LLM rewrite at translation boundaries — see
`src.standard.llm_rewriter`.
"""

from src.standard.llm_client import chat_completions, resolve_llm_config


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
        llm = resolve_llm_config(config)
        self.api_key = llm["api_key"]
        self.base_url = llm["base_url"]
        self.model = llm["model"]
        self.temperature = llm["temperature"]
        self.extra_headers = llm["extra_headers"]
        self.provider = llm["provider"]
        self.top_p = self.config.get("top_p", 0.9)
        self.rounds = self.config.get("rounds", 2)

    def _call_llm(self, system_prompt: str, text: str) -> str:
        return chat_completions(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text},
            ],
            api_key=self.api_key,
            base_url=self.base_url,
            model=self.model,
            temperature=self.temperature,
            top_p=self.top_p,
            timeout=60,
            extra_headers=self.extra_headers,
            provider=self.provider,
        )

    def process(self, text: str, **kwargs) -> str:
        rounds = kwargs.get("rounds", self.rounds)
        current_text = text

        for i in range(min(rounds, len(self.REWRITE_PROMPTS))):
            current_text = self._call_llm(self.REWRITE_PROMPTS[i], current_text)

        return current_text
