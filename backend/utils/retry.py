import logging
import random
import time
from collections.abc import Callable
from typing import TypeVar

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

            try:
                import openai as _openai  # noqa: PLC0415

                if isinstance(exc, _openai.RateLimitError):
                    is_retryable = True
                    retry_after = None
                    try:
                        retry_after = exc.response.headers.get("Retry-After")
                    except AttributeError:
                        pass
                    if retry_after is not None:
                        try:
                            delay = float(retry_after)
                        except (ValueError, TypeError):
                            pass
                elif isinstance(exc, _openai.APITimeoutError):
                    is_retryable = True
                elif isinstance(exc, _openai.APIConnectionError):
                    is_retryable = True
                elif isinstance(exc, _openai.InternalServerError):
                    is_retryable = True
            except ImportError:
                pass

            if not is_retryable:
                if isinstance(exc, requests.exceptions.Timeout):
                    is_retryable = True
                elif isinstance(exc, requests.exceptions.ConnectionError):
                    is_retryable = True
                elif isinstance(exc, requests.exceptions.HTTPError):
                    if hasattr(exc, "response") and exc.response is not None:
                        if exc.response.status_code in (429, 500, 503):
                            is_retryable = True
                            if exc.response.status_code == 429:
                                retry_after = exc.response.headers.get("Retry-After")
                                if retry_after is not None:
                                    try:
                                        delay = float(retry_after)
                                    except (ValueError, TypeError):
                                        pass

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
