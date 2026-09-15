"""Tests for retry_with_backoff (no network)."""

import httpx
import pytest

from src.standard.retry import retry_with_backoff, TRANSIENT_STATUS


def test_returns_on_first_success():
    calls = []

    def fn():
        calls.append(1)
        return "ok"

    assert retry_with_backoff(fn, max_retries=3, base_delay=0.01) == "ok"
    assert len(calls) == 1


def test_retries_on_transient_status(monkeypatch):
    """503 should be retried, then succeed."""
    attempts = {"n": 0}

    def fn():
        attempts["n"] += 1
        if attempts["n"] < 3:
            resp = httpx.Response(503, request=httpx.Request("POST", "http://x"))
            raise httpx.HTTPStatusError("err", request=resp.request, response=resp)
        return "recovered"

    result = retry_with_backoff(fn, max_retries=3, base_delay=0.01)
    assert result == "recovered"
    assert attempts["n"] == 3


def test_no_retry_on_client_error():
    """401 should NOT be retried."""
    attempts = {"n": 0}

    def fn():
        attempts["n"] += 1
        resp = httpx.Response(401, request=httpx.Request("POST", "http://x"))
        raise httpx.HTTPStatusError("err", request=resp.request, response=resp)

    with pytest.raises(httpx.HTTPStatusError):
        retry_with_backoff(fn, max_retries=3, base_delay=0.01)
    assert attempts["n"] == 1


def test_retries_on_timeout():
    attempts = {"n": 0}

    def fn():
        attempts["n"] += 1
        if attempts["n"] < 2:
            raise httpx.TimeoutException("timeout")
        return "ok"

    result = retry_with_backoff(fn, max_retries=3, base_delay=0.01)
    assert result == "ok"
    assert attempts["n"] == 2


def test_exhausts_retries():
    def fn():
        raise httpx.TimeoutException("timeout")

    with pytest.raises(httpx.TimeoutException):
        retry_with_backoff(fn, max_retries=2, base_delay=0.01)


def test_transient_status_codes():
    assert 429 in TRANSIENT_STATUS
    assert 502 in TRANSIENT_STATUS
    assert 503 in TRANSIENT_STATUS
    assert 401 not in TRANSIENT_STATUS
    assert 400 not in TRANSIENT_STATUS
