"""Translation engines: Google Translate and Niutrans."""

import httpx
from deep_translator import GoogleTranslator


def google_translate(text: str, source: str, target: str) -> str:
    """Translate text using Google Translate.

    Args:
        text: Text to translate.
        source: Source language code.
        target: Target language code.

    Returns:
        Translated text.
    """
    translator = GoogleTranslator(source=source, target=target)

    # Handle long texts by chunking (Google has ~5000 char limit)
    if len(text) > 4500:
        chunks = _split_text(text, max_len=4500)
        return " ".join(translator.translate(chunk) for chunk in chunks)

    return translator.translate(text)


def niutrans_translate(text: str, source: str, target: str, api_key: str) -> str:
    """Translate text using Niutrans API.

    Args:
        text: Text to translate.
        source: Source language code.
        target: Target language code.
        api_key: Niutrans API key.

    Returns:
        Translated text.
    """
    response = httpx.post(
        "https://api.niutrans.com/NiuTransServer/translation",
        json={
            "from": source,
            "to": target,
            "apikey": api_key,
            "src_text": text,
        },
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()

    if "tgt_text" in data:
        return data["tgt_text"]
    elif "error_msg" in data:
        raise RuntimeError(f"Niutrans error: {data['error_msg']}")
    else:
        raise RuntimeError(f"Unexpected Niutrans response: {data}")


def _split_text(text: str, max_len: int = 4500) -> list[str]:
    """Split text into chunks at sentence boundaries."""
    import re
    sentences = re.split(r'(?<=[.!?。！？])\s+', text)
    chunks = []
    current = ""

    for sentence in sentences:
        if len(current) + len(sentence) + 1 > max_len:
            if current:
                chunks.append(current)
            current = sentence
        else:
            current = f"{current} {sentence}".strip()

    if current:
        chunks.append(current)

    return chunks if chunks else [text]
