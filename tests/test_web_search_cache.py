from pathlib import Path

import pytest

from backend.config import settings
from backend.tools.web_search import SearchResult, WebSearchTool
from backend.utils.cache import _ensure_cache_table, _get_connection


class FakeProvider:
    def search(self, query: str) -> list[SearchResult]:
        return [SearchResult(title="Direct", url="https://direct.com", snippet="Direct hit")]


def test_web_search_direct_caches_on_fresh_db(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Ensure fresh DB path and enabled cache
    monkeypatch.setattr(settings, "db_path", str(tmp_path / "fresh_db.sqlite"))
    monkeypatch.setattr(settings, "cache_enabled", True)
    monkeypatch.setattr(settings, "cache_web_search_enabled", True)

    tool = WebSearchTool()
    monkeypatch.setattr(tool, "_provider", lambda: FakeProvider())

    # Run a search on a fresh DB. The table should be auto-created without error.
    results = tool.search("testing caching")
    assert len(results) == 1

    # Verify the table was created and caching happened
    with _get_connection() as conn:
        _ensure_cache_table(conn)
        cur = conn.cursor()
        count = cur.execute(
            "SELECT COUNT(*) FROM cache_entries WHERE kind = 'web_search'"
        ).fetchone()[0]
        assert count == 1
