import pytest

from backend.utils.credibility import score_source


def test_baseline_http() -> None:
    # baseline 0.4, no HTTPS bonus, no TLD bonus
    assert score_source("http://example.invalid") == 0.4


def test_https_adds_bonus() -> None:
    assert score_source("https://example.invalid") == 0.5


def test_gov_tld_bonus() -> None:
    score = score_source("https://nasa.gov")
    # baseline 0.4 + https 0.1 + gov 0.35 = 0.85
    assert score == 0.85


def test_mil_tld_bonus() -> None:
    score = score_source("https://navy.mil")
    assert score == 0.85


def test_edu_tld_bonus() -> None:
    score = score_source("https://mit.edu")
    # 0.4 + 0.1 + 0.25 = 0.75
    assert score == 0.75


def test_org_tld_small_bonus() -> None:
    score = score_source("https://random.org")
    # 0.4 + 0.1 + 0.05 = 0.55
    assert score == 0.55


def test_trusted_domain_bonus_stacks() -> None:
    # wikipedia.org gets the .org tld bonus + trusted-domain bonus
    score = score_source("https://en.wikipedia.org/wiki/X")
    # 0.4 + 0.1 + 0.05 + 0.15 = 0.7
    assert score == 0.7


def test_trusted_domain_iso() -> None:
    score = score_source("https://www.iso.org/standard/123.html")
    # 0.4 + 0.1 + 0.05 + 0.2 = 0.75
    assert score == 0.75


def test_score_is_clamped_to_one() -> None:
    # Synthetic URL designed to overshoot 1.0 without the clamp:
    #   baseline 0.4 + https 0.1 + gov 0.35 + trusted "iec.ch" substring 0.2 = 1.05
    # The trusted-domain check uses substring matching, so "iec.ch" appearing
    # anywhere in the netloc triggers the bonus.
    score = score_source("https://iec.ch.foo.gov")
    assert score == 1.0


def test_www_prefix_stripped() -> None:
    a = score_source("https://www.iso.org/x")
    b = score_source("https://iso.org/x")
    assert a == b


def test_no_tld_returns_baseline_plus_https() -> None:
    # localhost has no dot in netloc
    score = score_source("https://localhost")
    assert score == 0.5


def test_empty_string_url() -> None:
    assert score_source("") == 0.4


def test_ansi_and_ieee_trusted_domains() -> None:
    ansi_score = score_source("https://ansi.org")
    # 0.4 + 0.1 + 0.05 (.org) + 0.15 (ansi.org) = 0.7
    assert ansi_score == 0.7

    ieee_score = score_source("https://standards.ieee.org/spec")
    # 0.4 + 0.1 + 0.05 (.org) + 0.2 (standards.ieee.org) = 0.75
    assert ieee_score == 0.75


def test_url_with_query_params_and_fragment() -> None:
    score = score_source("https://iso.org/contents?section=1#heading")
    # 0.4 + 0.1 + 0.05 + 0.2 = 0.75
    assert score == 0.75


def test_non_http_https_scheme() -> None:
    score = score_source("ftp://iso.org/file.txt")
    # 0.4 (no https) + 0.05 (.org) + 0.2 (iso.org) = 0.65
    assert score == 0.65


def test_urlparse_exception_handled(monkeypatch: pytest.MonkeyPatch) -> None:
    def mock_urlparse_raises(url: str) -> None:
        raise ValueError("Malformed URL")

    import backend.utils.credibility as cred

    monkeypatch.setattr(cred, "urlparse", mock_urlparse_raises)

    assert cred.score_source("https://broken-url") == 0.5
    assert cred.score_source("http://broken-url") == 0.4
