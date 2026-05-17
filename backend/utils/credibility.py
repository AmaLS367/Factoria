from urllib.parse import urlparse

TRUSTED_DOMAINS: dict[str, float] = {
    "wikipedia.org": 0.15,
    "iso.org": 0.2,
    "iec.ch": 0.2,
    "ansi.org": 0.15,
    "standards.ieee.org": 0.2,
}


def score_source(url: str) -> float:
    """Return a 0.0–1.0 credibility score for a source URL based on heuristics."""
    score = 0.4

    if url.startswith("https://"):
        score += 0.1

    try:
        domain = urlparse(url).netloc.lower().removeprefix("www.")
    except Exception:
        return round(score, 3)

    tld = domain.rsplit(".", 1)[-1] if "." in domain else ""

    if tld in ("gov", "mil"):
        score += 0.35
    elif tld == "edu":
        score += 0.25
    elif tld == "org":
        score += 0.05

    for trusted_domain, bonus in TRUSTED_DOMAINS.items():
        if trusted_domain in domain:
            score += bonus
            break

    return round(min(max(score, 0.0), 1.0), 3)
