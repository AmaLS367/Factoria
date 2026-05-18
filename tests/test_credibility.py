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
