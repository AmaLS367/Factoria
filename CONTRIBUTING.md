<h1 align="center">🤝 Contributing</h1>

<p align="center">
  <strong>Small, focused, verifiable changes for an AI data collection toolkit.</strong>
</p>

<p align="center">
  <a href="README.md">🏠 README</a> ·
  <a href="SECURITY.md">🛡️ Security</a> ·
  <a href="CODE_OF_CONDUCT.md">📜 Code of Conduct</a>
</p>

---

## ⚡ Fast Path

```powershell
uv sync
uv run ruff check .
uv run mypy .
```

For local collection runs:

```powershell
Copy-Item .env.example .env
uv run python backend/main.py
```

## 🧭 Contribution Map

| Change type | Start here | Required check |
| --- | --- | --- |
| LLM behavior | `backend/clients`, `backend/promts` | Sanitized prompt/response example |
| Batch runner | `backend/main.py` | `ruff` + `mypy` + sample input check |
| CLI behavior | `backend/cli.py` | Manual single-item run |
| Storage/export | `backend/utils/db_writer.py`, Excel export code | SQLite + XLSX smoke check |
| Configuration | `backend/config.py`, `.env.example` | Document new env values |
| Docs/assets | `README.md`, `docs/assets` | Link/path check |

## 🌿 Branch Names

Use short, scoped branch names:

- `docs/readme-polish`
- `fix/parser-empty-response`
- `refactor/llm-client`
- `feat/custom-target-fields`
- `test/db-writer`

## ✅ Pull Request Checklist

Before opening a PR:

- [ ] Run `uv run ruff check .`.
- [ ] Run `uv run mypy .`.
- [ ] Keep the PR focused on one concern.
- [ ] Explain config, prompt, provider, or output format changes.
- [ ] Include sanitized examples only.
- [ ] Do not commit local `.env`, databases, logs, or real collected data.

## 🔒 Never Commit

Use real secrets only in ignored local files. Never commit:

- `.env`
- API keys or provider tokens
- real customer/vendor/item datasets
- generated SQLite databases with private data
- exported reports with private data
- `collector.log` with sensitive prompts or responses
- local virtual environments or cache directories

## 🧾 Commit Style

Prefer concise concern-based commits:

- `docs: polish readme`
- `fix(parser): handle empty llm response`
- `refactor(config): clarify target fields`
- `feat(cli): add single item mode`
- `test: cover sqlite writer`

## 📚 Related Docs

- [README](README.md)
- [Security policy](SECURITY.md)
- [Code of Conduct](CODE_OF_CONDUCT.md)
