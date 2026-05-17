import logging
import random
import time
from collections.abc import Callable
from typing import TypeVar

import openai
import requests

logger = logging.getLogger(__name__)

T = TypeVar("T")


def with_retry(
    fn: Callable[[], T],
    *,
    max_attempts: int,
    base_delay: float,
    max_delay: float,
    label: str = "",
) -> T:
    """Call fn(), retrying on retryable errors with exponential backoff + jitter."""
    attempt = 0
    while True:
        try:
            result = fn()
            if attempt > 0:
                logger.info("Recovered after %d retries for %s", attempt, label)
            return result
        except Exception as exc:
            attempt += 1
            is_retryable = False
            delay = 0.0

            if isinstance(exc, openai.RateLimitError):
                is_retryable = True
                try:
                    delay = int(exc.response.headers.get("Retry-After", base_delay))
                except (ValueError, TypeError, AttributeError):
                    delay = base_delay
            elif isinstance(exc, openai.APITimeoutError):
                is_retryable = True
            elif isinstance(exc, openai.APIConnectionError):
                is_retryable = True
            elif isinstance(exc, openai.InternalServerError):
                # Status 500 or 503 is retryable
                is_retryable = True
            elif isinstance(exc, requests.exceptions.Timeout):
                is_retryable = True
            elif isinstance(exc, requests.exceptions.ConnectionError):
                is_retryable = True
            elif isinstance(exc, requests.exceptions.HTTPError):
                if hasattr(exc, "response") and exc.response is not None:
                    if exc.response.status_code in (429, 500, 503):
                        is_retryable = True
                        if exc.response.status_code == 429:
                            try:
                                delay = int(exc.response.headers.get("Retry-After", base_delay))
                            except (ValueError, TypeError, AttributeError):
                                delay = base_delay

            if not is_retryable:
                raise

            if attempt >= max_attempts:
                logger.error("All %d attempts failed for %s: %s", max_attempts, label, exc)
                raise

            if delay == 0.0:
                delay = min(base_delay * (2 ** (attempt - 1)) + random.uniform(0, 1), max_delay)

            logger.warning(
                "Retry %d/%d for %s in %.1fs: %s", attempt, max_attempts, label, delay, exc
            )
            time.sleep(delay)
