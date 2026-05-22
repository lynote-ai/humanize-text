"""DeepSeek LLM humanization rewriter.

Uses DeepSeek API with temperature 1.3 to translate and humanize text.
Carries previous round history for context-aware rewriting.
"""

import httpx

SYSTEM_PROMPT = "你是一个专业的文案改写专家,精通多语言本地化。"


def deepseek_rewrite(
    text: str,
    target_language: str,
    api_key: str,
    history: dict | None = None,
    model: str = "deepseek-chat",
    temperature: float = 1.3,
) -> str:
    """Rewrite text into target language with humanization.

    Args:
        text: Input text to rewrite.
        target_language: Target language name (e.g., "中文", "日语").
        api_key: DeepSeek API key.
        history: Optional dict with 'input' and 'output' from previous round.
        model: DeepSeek model name.
        temperature: Sampling temperature (1.3 recommended for humanization).

    Returns:
        Humanized text in target language.
    """
    user_prompt = f"翻译为{target_language}，去掉 AI 味道，拟人化改写，只输出结果：\n{text}"

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Carry previous round as context if available
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

    response = httpx.post(
        "https://api.deepseek.com/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": model,
            "temperature": temperature,
            "messages": messages,
        },
        timeout=120,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"].strip()
