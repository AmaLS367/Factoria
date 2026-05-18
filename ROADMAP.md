# Factoria — Roadmap

Legend: ✅ done · 🔲 pending

---

| #  | Feature                                                                                                                                                                | Status |
| -- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| 1  | **Proper database & migrations** — split results into items/item_fields/item_sources/runs, versioned migrations, safe upgrades of existing SQLite databases     | ✅     |
| 2  | **Multi-provider LLM support** — OpenAI, DeepSeek, Gemini, Nvidia, OpenRouter, ModelScope, Together, Groq, local Ollama models via a unified provider interface | ✅     |
| 3  | **Basic frontend** — Excel upload, field configuration, collection progress, result download                                                                    | ✅     |
| 4  | **FastAPI backend** — API for jobs, items, exports, search, and settings; CLI remains as a thin client                                                          | ✅     |
| 5  | **Job queue & background tasks** — queued/running/failed/completed statuses, resume/retry/cancel, large Excel files without blocking the process                | ✅     |
| 6  | **80%+ test coverage** — unit/integration tests for parser, DB, CLI, agents, providers, Excel import/export, migrations, and failure modes                      | ✅     |
| 7  | **Proper Excel/CSV import** — column preview, validation, column mapping, CSV/XLSX support, multiple sheets, clean error messages                               | ✅     |
| 8  | **Smart deduplication & caching** — skip LLM/web-search for already-collected items; cache keyed by item/query/provider/model                                   | ✅     |
| 9  | **Source credibility & citation quality** — rank sources, store title/url/snippet/provider/retrieved_at, credibility score                                      | ✅     |
| 10 | **Schema templates / project presets** — saved templates for spare parts, suppliers, products, companies, technical specs, etc.                                 | ✅     |
| 11 | **LLM response validation via Pydantic** — strict schemas, retries on invalid output, field-level validation                                                    | ✅     |
| 12 | **Retry/backoff/rate-limit layer** — universal retry for LLM and search providers, limits, cooldown, proper error diagnostics                                   | ✅     |
| 13 | **Observability & structured logs** — job logs, per-item logs, latency, provider errors; GET /logs endpoint + Logs tab in UI                                    | ✅     |
| 14 | **Cost/token accounting** — track tokens, estimated cost, request count, per-job pricing, exportable report                                                     | 🔲     |
| 15 | **Human review workflow** — UI/CLI mode to manually confirm or correct uncertain/empty/low-confidence fields                                                    | 🔲     |
| 16 | **Confidence scoring** — per-field confidence: found in sources / corroborated across sources / model guessed / not found                                       | ✅     |
| 17 | **Plugin/tool architecture for agents** — unified registry for tools: web search, file lookup, DB lookup, vendor APIs, browser extraction                       | 🔲     |
| 18 | **HTML/PDF/document extraction** — agent opens found PDFs/spec sheets/manuals, extracts text, and uses it as evidence                                           | 🔲     |
| 19 | **Docker packaging & one-command deploy** — docker compose up, volume for SQLite/results, healthcheck, production-ready env handling                            | 🔲     |
| 20 | **Documentation site + examples** — quickstart, providers, .env, Excel examples, migration guide, API docs, troubleshooting                                     | 🔲     |

---

**Progress: 14 / 20 done**
