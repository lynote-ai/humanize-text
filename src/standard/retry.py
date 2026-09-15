"""Retry with exponential backoff for transient API failures."""

import time
from typing import Callable, TypeVar

import httpx

T = TypeVar("T")

# HTTP status codes that indicate a transient error worth retrying
TRANSIENT_STATUS = frozenset({408, 429, 502, 503, 504})


def retry_with_backoff(
    fn: Callable[[], T],
    *,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
) -> T:
    """Call fn() with up to max_retries retries on transient errors.

    Retries on:
      - httpx.HTTPStatusError with status in TRANSIENT_STATUS
      - httpx.TimeoutException
      - httpx.ConnectError / httpx.NetworkError

    Does NOT retry on 4xx client errors (401, 400, 422, etc.) — those
    won't recover on retry.
    """
    last_exc: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            return fn()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code not in TRANSIENT_STATUS:
                raise
            last_exc = exc
        except (httpx.TimeoutException, httpx.ConnectError, httpx.NetworkError) as exc:
            last_exc = exc

        if attempt < max_retries:
            delay = min(base_delay * (2 ** attempt), max_delay)
            time.sleep(delay)

    raise last_exc  # type: ignore[misc]
