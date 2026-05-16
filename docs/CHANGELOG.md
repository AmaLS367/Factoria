# Changelog

All notable changes to Factoria are documented here.

## v0.1.0 - 2026-05-16

Initial public baseline for Factoria as a repeatable AI data collection toolkit.

### Added

- Excel batch collection from a configured sheet and identifier column.
- Single-item CLI collection with Rich terminal output.
- Provider-based LLM client with OpenAI-compatible APIs, Gemini, and Ollama support.
- Web search enrichment through Tavily, Brave Search, and DDGS fallback.
- Research agent that combines web search context with LLM extraction.
- SQLite checkpointing with versioned migrations and normalized storage.
- Formatted Excel export for collected results.
- FastAPI backend with health, settings, search, collect, jobs, items, and export endpoints.
- README positioning updates for use cases, provider support, and ChatGPT comparison.

### Changed

- Renamed the Python project package metadata from `parts-info-collector` to `factoria`.
- Updated repository metadata to point at `AmaLS367/Factoria`.
- Reworked storage from a dynamic wide `results` table toward migrated SQLite tables.
- Kept legacy `OPENAI_*` configuration while adding `LLM_*` provider settings.

### Notes

- Frontend UI is not included in this release.
- Demo video/GIF assets are intentionally deferred until the frontend exists.
