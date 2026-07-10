#!/usr/bin/env python3
"""Retry helper for Microsoft Dataverse Web API service protection limits.

Honors the `Retry-After` response header returned with HTTP 429 (Too Many
Requests) and falls back to exponential backoff when the header is absent.
Works with any HTTP client whose response object exposes a `.status_code` int
and a `.headers` mapping (e.g. `requests.Response`). Pass your own send-callable
or session so calls stay injectable and unit-testable.

Verify the backoff logic offline (no network or credentials):
    python dataverse_retry.py --self-test
"""
from __future__ import annotations

import argparse
import sys
import time

# Service protection error codes returned in OrganizationServiceFault.ErrorDetails
# (SDK for .NET). The Web API returns the matching hex codes. See
# references/error-codes-and-limits.md for full messages and default limits.
SERVICE_PROTECTION_ERROR_CODES = {
    -2147015902: "Number of requests exceeded the limit of 6000 over 300 seconds.",
    -2147015903: "Combined execution time exceeded limit of 1,200,000 ms over 300 seconds.",
    -2147015898: "Number of concurrent requests exceeded the limit of 52.",
}

# Headers Dataverse returns for rate-limit debugging and parallelism tuning.
RATE_LIMIT_HEADERS = (
    "x-ms-ratelimit-burst-remaining-xrm-requests",  # remaining requests, this connection
    "x-ms-ratelimit-time-remaining-xrm-requests",   # remaining combined execution time, this user
    "x-ms-dop-hint",                                 # recommended degree of parallelism
)


def retry_delay_seconds(headers, attempt, base=2.0, max_delay=300.0):
    """Return how long to wait (seconds) before the next retry.

    Prefers the server-provided `Retry-After` value (an integer count of
    seconds). Falls back to exponential backoff `base ** attempt`, capped at
    `max_delay`, when the header is missing or not an integer (e.g. an
    HTTP-date form).
    """
    headers = headers or {}
    for key in ("Retry-After", "retry-after"):  # be case-insensitive
        if key in headers:
            try:
                return float(int(str(headers[key]).strip()))
            except (ValueError, TypeError):
                break  # non-integer (HTTP-date): fall through to backoff
    return min(base ** max(attempt, 0), max_delay)


def rate_limit_status(headers):
    """Return the rate-limit debugging headers as a dict (missing -> None).

    For debugging only. Do not throttle client behavior from these values:
    they reset when requests land on a different web server (affinity cookie off).
    """
    headers = headers or {}
    return {h: headers.get(h) for h in RATE_LIMIT_HEADERS}


def request_with_retry(send, *, max_retries=10, sleep=time.sleep, on_retry=None):
    """Call `send()` (a zero-arg callable returning a response) with retry on 429.

    Retries up to `max_retries` times, waiting `retry_delay_seconds` between
    attempts. Returns the final response (which may still be a 429 if retries
    are exhausted). `on_retry(attempt, delay, response)` is invoked before each
    sleep, if provided.
    """
    attempt = 0
    while True:
        response = send()
        if getattr(response, "status_code", None) != 429:
            return response
        if attempt >= max_retries:
            return response
        delay = retry_delay_seconds(getattr(response, "headers", {}), attempt)
        if on_retry:
            on_retry(attempt, delay, response)
        sleep(delay)
        attempt += 1


def call(session, method, url, *, max_retries=10, **kwargs):
    """Convenience wrapper around a `requests`-style session with retry.

    Example:
        import requests
        s = requests.Session()
        s.headers.update({"Authorization": f"Bearer {token}", ...})
        r = call(s, "POST", f"{org_url}/api/data/v9.2/accounts", json={...})
    """
    return request_with_retry(
        lambda: session.request(method, url, **kwargs), max_retries=max_retries
    )


def _self_test():
    # Retry-After header honored, case-insensitive.
    assert retry_delay_seconds({"Retry-After": "7"}, attempt=0) == 7.0
    assert retry_delay_seconds({"retry-after": "3"}, attempt=5) == 3.0

    # Exponential backoff fallback and cap.
    assert retry_delay_seconds({}, attempt=0) == 1.0
    assert retry_delay_seconds({}, attempt=3) == 8.0
    assert retry_delay_seconds({}, attempt=20, max_delay=300) == 300.0

    # Non-integer Retry-After (HTTP-date) falls back to backoff.
    assert retry_delay_seconds(
        {"Retry-After": "Wed, 21 Oct 2099 07:28:00 GMT"}, attempt=2
    ) == 4.0

    class _Resp:
        def __init__(self, status, headers=None):
            self.status_code = status
            self.headers = headers or {}

    # Loop: 429, 429, then 200. Two sleeps, three calls.
    seq = [_Resp(429, {"Retry-After": "0"}), _Resp(429, {"Retry-After": "0"}), _Resp(200)]
    calls = {"i": 0}

    def send():
        r = seq[calls["i"]]
        calls["i"] += 1
        return r

    slept = []
    final = request_with_retry(send, max_retries=5, sleep=slept.append)
    assert final.status_code == 200
    assert calls["i"] == 3
    assert slept == [0.0, 0.0]

    # max_retries respected when always 429: 1 initial + max_retries attempts.
    counter = {"n": 0}

    def always_429():
        counter["n"] += 1
        return _Resp(429, {"Retry-After": "0"})

    out = request_with_retry(always_429, max_retries=2, sleep=lambda _s: None)
    assert out.status_code == 429
    assert counter["n"] == 3  # initial + 2 retries

    # rate_limit_status extraction.
    status = rate_limit_status({"x-ms-dop-hint": "8"})
    assert status["x-ms-dop-hint"] == "8"
    assert status["x-ms-ratelimit-burst-remaining-xrm-requests"] is None

    print("All self-tests passed.")


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Dataverse Web API 429 retry helper.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--self-test", action="store_true", help="Run offline tests and exit."
    )
    args = parser.parse_args(argv)
    if args.self_test:
        _self_test()
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
