"""OpenAI-compatible LLM client with multi-provider config resolution."""

from __future__ import annotations

import os
from typing import Any

import httpx

PROVIDER_DEFAULTS: dict[str, dict[str, str]] = {
    "deepseek": {
        "base_url": "https://api.deepseek.com",
        "model": "deepseek-chat",
        "api_key_field": "deepseek_api_key",
        "display_name": "DeepSeek",
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "model": "deepseek/deepseek-chat",
        "api_key_field": "openrouter_api_key",
        "display_name": "OpenRouter",
    },
    "litellm": {
        "base_url": "",
        "model": "deepseek/deepseek-chat",
        "api_key_field": "litellm_api_key",
        "display_name": "LiteLLM",
    },
}

DEFAULT_PROVIDER = "deepseek"


def normalize_chat_completions_url(base_url: str) -> str:
    """Ensure base_url points at the chat completions endpoint."""
    base = base_url.rstrip("/")
    if base.endswith("/chat/completions"):
        return base
    return f"{base}/chat/completions"


def resolve_llm_config(config: dict) -> dict[str, Any]:
    """Merge TOML config and environment variables into resolved LLM settings."""
    llm_cfg = config.get("llm", {})
    pipeline_cfg = config.get("pipeline", {})
    api_keys = config.get("api_keys", {})

    provider = llm_cfg.get("provider") or DEFAULT_PROVIDER
    if env_provider := os.environ.get("LLM_PROVIDER"):
        provider = env_provider

    if provider not in PROVIDER_DEFAULTS:
        raise ValueError(
            f"Unsupported LLM provider: {provider!r}. "
            f"Supported: {', '.join(PROVIDER_DEFAULTS)}"
        )

    defaults = PROVIDER_DEFAULTS[provider]

    base_url = llm_cfg.get("base_url") or defaults["base_url"]
    if env_base_url := os.environ.get("LLM_BASE_URL"):
        base_url = env_base_url

    model = llm_cfg.get("model") or pipeline_cfg.get("model") or defaults["model"]
    if env_model := os.environ.get("LLM_MODEL"):
        model = env_model

    temperature = llm_cfg.get("temperature", pipeline_cfg.get("temperature", 1.3))

    api_key_field = defaults["api_key_field"]
    api_key = api_keys.get(api_key_field, "")

    if env_api_key := os.environ.get("LLM_API_KEY"):
        api_key = env_api_key
    elif provider == "openrouter" and (or_key := os.environ.get("OPENROUTER_API_KEY")):
        api_key = or_key
    elif provider == "deepseek" and (ds_key := os.environ.get("DEEPSEEK_API_KEY")):
        api_key = ds_key

    if not api_key and provider != "litellm":
        raise ValueError(
            f"Missing API key for provider {provider!r}. "
            f"Set api_keys.{api_key_field} in config or LLM_API_KEY env var."
        )

    extra_headers: dict[str, str] = {}
    if http_referer := llm_cfg.get("http_referer"):
        extra_headers["HTTP-Referer"] = http_referer
    if app_title := llm_cfg.get("app_title"):
        extra_headers["X-Title"] = app_title

    return {
        "provider": provider,
        "display_name": defaults["display_name"],
        "base_url": base_url,
        "model": model,
        "temperature": temperature,
        "api_key": api_key,
        "extra_headers": extra_headers or None,
    }


def chat_completions(
    messages: list[dict],
    *,
    api_key: str,
    base_url: str,
    model: str,
    temperature: float = 1.3,
    top_p: float | None = None,
    timeout: int = 120,
    extra_headers: dict | None = None,
    provider: str | None = None,
) -> str:
    """Call an OpenAI-compatible /chat/completions endpoint."""
    if provider == "litellm":
        return _litellm_chat_completions(
            messages,
            api_key=api_key,
            model=model,
            temperature=temperature,
            top_p=top_p,
            timeout=timeout,
        )

    if not api_key:
        raise ValueError("API key is required for LLM chat completions.")

    url = normalize_chat_completions_url(base_url)
    headers = {"Authorization": f"Bearer {api_key}"}
    if extra_headers:
        headers.update(extra_headers)

    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }
    if top_p is not None:
        payload["top_p"] = top_p

    response = httpx.post(url, headers=headers, json=payload, timeout=timeout)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"].strip()


def _litellm_chat_completions(
    messages: list[dict],
    *,
    api_key: str,
    model: str,
    temperature: float = 1.3,
    top_p: float | None = None,
    timeout: int = 120,
) -> str:
    """Route through LiteLLM SDK for 100+ provider support."""
    import litellm

    kwargs: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "drop_params": True,
        "timeout": timeout,
    }
    if api_key:
        kwargs["api_key"] = api_key
    if top_p is not None:
        kwargs["top_p"] = top_p

    response = litellm.completion(**kwargs)
    return response.choices[0].message.content.strip()
