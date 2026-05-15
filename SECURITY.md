<h1 align="center">🛡️ Security Policy</h1>

<p align="center">
  <strong>Protect API keys, prompts, collected data, exports, and local runtime files.</strong>
</p>

<p align="center">
  <a href="README.md">🏠 README</a> ·
  <a href="CONTRIBUTING.md">🤝 Contributing</a> ·
  <a href="CODE_OF_CONDUCT.md">📜 Code of Conduct</a>
</p>

---

## ✅ Supported Branches

| Branch | Status |
| --- | --- |
| `main` | Supported for security fixes |
| older branches | Not supported |

## 🚫 Sensitive Data

Never publish or attach these files or values in public issues, pull requests, screenshots, logs, or comments:

| Do not publish | Why |
| --- | --- |
| `.env` | Contains API keys and provider configuration |
| API keys or provider tokens | Can allow paid model access |
| raw input spreadsheets | May contain private item, vendor, or customer data |
| SQLite databases | May contain collected private data |
| exported Excel reports | May contain enriched private data |
| `collector.log` | May contain prompts, identifiers, or errors with sensitive context |
| full LLM prompts/responses | May reveal private data or provider credentials |

Use `.env.example` and sanitized rows for public examples.

## 📣 Reporting a Vulnerability

If the report includes secrets, private datasets, provider tokens, or a working exploit path, do **not** open a public issue.

Send the maintainer a private report through the contact channel listed on the repository profile, or open a minimal public issue that says a private security report is needed without including sensitive details.

Include:

- affected file, command, or component;
- expected vs actual behavior;
- reproduction steps without real credentials;
- suggested severity;
- whether API keys, input data, SQLite rows, logs, or exported reports may be exposed.

## 🔐 Runtime Boundaries

Factoria is a local data collection tool. Treat local runtime files as sensitive.

| Area | Intended use |
| --- | --- |
| `.env` | Local provider configuration only |
| `backend/input` or configured input path | Local spreadsheet input |
| `results/database.sqlite` | Local checkpoint database |
| `results/output.xlsx` | Local exported report |
| `collector.log` | Local operational log |

Do not upload runtime data unless it has been reviewed and sanitized.

## 🧪 Security Checks

Relevant check areas:

- secret handling in `.env` and logs;
- provider errors that may echo sensitive values;
- parser behavior for malformed model output;
- database/export paths;
- accidental commits of runtime data;
- examples that include real identifiers.

Run:

```powershell
uv run ruff check .
uv run mypy .
```
