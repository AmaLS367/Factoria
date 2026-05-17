from unittest.mock import Mock, patch

import openai
import pytest
import requests

from backend.utils.retry import with_retry


def test_success_on_first_attempt() -> None:
    fn = Mock(return_value="success")
    with patch("time.sleep") as mock_sleep:
        result = with_retry(
            fn, max_attempts=3, base_delay=1.0, max_delay=10.0, label="test/success"
        )
    assert result == "success"
    fn.assert_called_once()
    mock_sleep.assert_not_called()


def test_retry_on_requests_httperror_429_success_second_attempt() -> None:
    mock_response = Mock()
    mock_response.status_code = 429
    # Ensure headers don't have Retry-After or we parse it specifically
    mock_response.headers = {}
    exc = requests.exceptions.HTTPError(response=mock_response)

    fn = Mock(side_effect=[exc, "success"])

    with patch("time.sleep") as mock_sleep, patch("random.uniform", return_value=0.0):
        result = with_retry(fn, max_attempts=3, base_delay=1.0, max_delay=10.0, label="test/429")

    assert result == "success"
    assert fn.call_count == 2
    mock_sleep.assert_called_once_with(1.0)  # base_delay * (2**0) + 0.0


def test_retry_on_requests_timeout_exhausts_all_attempts() -> None:
    exc = requests.exceptions.Timeout("timeout")
    fn = Mock(side_effect=exc)

    with patch("time.sleep") as mock_sleep, patch("random.uniform", return_value=0.0):
        with pytest.raises(requests.exceptions.Timeout):
            with_retry(fn, max_attempts=3, base_delay=1.0, max_delay=10.0, label="test/timeout")

    assert fn.call_count == 3
    assert mock_sleep.call_count == 2
    mock_sleep.assert_any_call(1.0)  # attempt 1
    mock_sleep.assert_any_call(2.0)  # attempt 2


def test_non_retryable_exception() -> None:
    exc = ValueError("bad value")
    fn = Mock(side_effect=exc)

    with patch("time.sleep") as mock_sleep:
        with pytest.raises(ValueError):
            with_retry(fn, max_attempts=3, base_delay=1.0, max_delay=10.0, label="test/valueerror")

    fn.assert_called_once()
    mock_sleep.assert_not_called()


def test_retry_after_header_on_429() -> None:
    mock_response = Mock()
    mock_response.status_code = 429
    mock_response.headers = {"Retry-After": "5"}
    exc = requests.exceptions.HTTPError(response=mock_response)

    fn = Mock(side_effect=[exc, "success"])

    with patch("time.sleep") as mock_sleep:
        result = with_retry(
            fn, max_attempts=3, base_delay=1.0, max_delay=10.0, label="test/429_header"
        )

    assert result == "success"
    assert fn.call_count == 2
    mock_sleep.assert_called_once_with(5)


def test_openai_ratelimiterror_with_retry_after() -> None:
    mock_response = Mock()
    mock_response.status_code = 429
    mock_response.headers = {"Retry-After": "10"}
    exc = openai.RateLimitError("rate limited", response=mock_response, body={})

    fn = Mock(side_effect=[exc, "success"])

    with patch("time.sleep") as mock_sleep:
        result = with_retry(
            fn, max_attempts=3, base_delay=1.0, max_delay=10.0, label="test/openai_429"
        )

    assert result == "success"
    assert fn.call_count == 2
    mock_sleep.assert_called_once_with(10)
