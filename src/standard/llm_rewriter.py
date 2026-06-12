"""LLM humanization rewriter (OpenAI-compatible providers).

Supports DeepSeek, OpenRouter, and any compatible endpoint via config.
Carries previous round history for context-aware rewriting.
"""

from .llm_client import chat_completions

SYSTEM_PROMPT = "你是一个专业的文案改写专家,精通多语言本地化。"


def llm_rewrite(
    text: str,
    target_language: str,
    api_key: str,
    base_url: str,
    model: str,
    history: dict | None = None,
    temperature: float = 1.3,
    extra_headers: dict | None = None,
    provider: str | None = None,
) -> str:
    """Rewrite text into target language with humanization.

    Args:
        text: Input text to rewrite.
        target_language: Target language name (e.g., "中文", "日语").
        api_key: LLM provider API key.
        base_url: Provider base URL (OpenAI-compatible).
        model: Model name / slug.
        history: Optional dict with 'input' and 'output' from previous round.
        temperature: Sampling temperature (1.3 recommended for humanization).
        extra_headers: Optional extra HTTP headers (e.g. OpenRouter attribution).

    Returns:
        Humanized text in target language.
    """
    user_prompt = f"翻译为{target_language}，去掉 AI 味道，拟人化改写，只输出结果：\n{text}"

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    if history:
        messages.append({
            "role": "user",
            "content": f"翻译为{target_language}，去掉 AI 味道，拟人化改写，只输出结果：\n{history['input']}",
        })
        messages.append({
            "role": "assistant",
            "content": history["output"],
        })

    messages.append({"role": "user", "content": user_prompt})

    return chat_completions(
        messages,
        api_key=api_key,
        base_url=base_url,
        model=model,
        temperature=temperature,
        extra_headers=extra_headers,
        provider=provider,
    )


def deepseek_rewrite(
    text: str,
    target_language: str,
    api_key: str,
    history: dict | None = None,
    model: str = "deepseek-chat",
    temperature: float = 1.3,
    base_url: str = "https://api.deepseek.com",
    extra_headers: dict | None = None,
) -> str:
    """Backward-compatible alias for direct DeepSeek usage."""
    return llm_rewrite(
        text=text,
        target_language=target_language,
        api_key=api_key,
        base_url=base_url,
        model=model,
        history=history,
        temperature=temperature,
        extra_headers=extra_headers,
    )
