#!/bin/bash
# Re-run all steps since it seems they were lost.

# 1. backend/utils/schemas.py
cat << 'PY_EOF' >> backend/utils/schemas.py

from dataclasses import dataclass

@dataclass
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0

    def __add__(self, other: "TokenUsage") -> "TokenUsage":
        return TokenUsage(
            prompt_tokens=self.prompt_tokens + other.prompt_tokens,
            completion_tokens=self.completion_tokens + other.completion_tokens,
            total_tokens=self.total_tokens + other.total_tokens,
            estimated_cost_usd=round(self.estimated_cost_usd + other.estimated_cost_usd, 8),
        )
PY_EOF

# 2. backend/utils/pricing.py
cat << 'PY_EOF' > backend/utils/pricing.py
from backend.config import settings

_PRICE_TABLE: dict[str, tuple[float, float]] = {
    "gpt-4o-mini":        (0.000150, 0.000600),
    "gpt-4o":             (0.002500, 0.010000),
    "gpt-4-turbo":        (0.010000, 0.030000),
    "gpt-4":              (0.030000, 0.060000),
    "gpt-3.5-turbo":      (0.000500, 0.001500),
    "deepseek-chat":      (0.000270, 0.001100),
    "deepseek-coder":     (0.000270, 0.001100),
    "gemini-2.0-flash":   (0.000075, 0.000300),
    "gemini-1.5-flash":   (0.000075, 0.000300),
    "gemini-1.5-pro":     (0.001250, 0.005000),
    "llama":              (0.0, 0.0),
    "mistral":            (0.0, 0.0),
    "qwen":               (0.0, 0.0),
}

def get_price_per_1k(model: str) -> tuple[float, float]:
    """Return (input_usd_per_1k, output_usd_per_1k) for model, or config fallback."""
    lower = model.lower()
    for key, prices in _PRICE_TABLE.items():
        if key in lower:
            return prices
    return settings.llm_cost_per_1k_input_tokens, settings.llm_cost_per_1k_output_tokens

def estimate_cost(prompt_tokens: int, completion_tokens: int, model: str) -> float:
    inp, out = get_price_per_1k(model)
    return round((prompt_tokens / 1000) * inp + (completion_tokens / 1000) * out, 8)
PY_EOF

# 3. backend/config.py
sed -i '/llm_validation_max_attempts: int = 2/a \
    llm_cost_per_1k_input_tokens: float = 0.0\
    llm_cost_per_1k_output_tokens: float = 0.0' backend/config.py

# 4. backend/clients/llm_client.py
cat << 'PY_EOF' > patch_llm_client.py
import re

with open("backend/clients/llm_client.py", "r") as f:
    code = f.read()

code = code.replace("from backend.config import settings", "from backend.config import settings\nfrom backend.utils.schemas import TokenUsage\nfrom backend.utils.pricing import estimate_cost")

code = code.replace("def get_answer(self, prompt: str) -> str:", "def get_answer(self, prompt: str) -> tuple[str, TokenUsage]:")

openai_patch = """        def _call() -> tuple[str, TokenUsage]:
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": settings.system_prompt},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.1,
                    timeout=settings.resolved_llm_timeout_seconds,
                )
                text = response.choices[0].message.content or ""
                usage = response.usage
                pt = (usage.prompt_tokens or 0) if usage else 0
                ct = (usage.completion_tokens or 0) if usage else 0
                cost = estimate_cost(pt, ct, self.model_name)
                return text, TokenUsage(prompt_tokens=pt, completion_tokens=ct, total_tokens=pt + ct, estimated_cost_usd=cost)
            except Exception:
                return "", TokenUsage()

        try:
            return with_retry(
                _call,
                max_attempts=settings.retry_max_attempts,
                base_delay=settings.retry_base_delay_seconds,
                max_delay=settings.retry_max_delay_seconds,
                label="llm/openai",
            )
        except Exception as e:
            logger.error(f"OpenAI error: {e}")
            return "", TokenUsage()"""
code = re.sub(r"        def _call\(\) -> str:.*?return \"\"", openai_patch, code, flags=re.DOTALL, count=1)

gemini_patch = """        def _call() -> tuple[str, TokenUsage]:
            try:
                response = requests.post(
                    url, json=payload, timeout=settings.resolved_llm_timeout_seconds
                )
                response.raise_for_status()
                data = response.json()
                meta = data.get("usageMetadata", {})
                pt = meta.get("promptTokenCount", 0) or 0
                ct = meta.get("candidatesTokenCount", 0) or 0
                cost = estimate_cost(pt, ct, self.model_name)
                try:
                    text = data["candidates"][0]["content"]["parts"][0]["text"]
                    text = cast(str, text)
                except (KeyError, IndexError):
                    logger.error(f"Unexpected Gemini API response structure: {data}")
                    text = ""
                return text, TokenUsage(prompt_tokens=pt, completion_tokens=ct, total_tokens=meta.get("totalTokenCount", pt + ct) or (pt + ct), estimated_cost_usd=cost)
            except Exception:
                return "", TokenUsage()

        try:
            return with_retry(
                _call,
                max_attempts=settings.retry_max_attempts,
                base_delay=settings.retry_base_delay_seconds,
                max_delay=settings.retry_max_delay_seconds,
                label="llm/gemini",
            )
        except Exception as e:
            logger.error(f"Gemini error: {e}")
            return "", TokenUsage()"""
code = re.sub(r"        def _call\(\) -> str:(.*?)(?=class OllamaProvider)", gemini_patch + "\n\n", code, flags=re.DOTALL, count=1)

ollama_patch = """        def _call() -> tuple[str, TokenUsage]:
            try:
                response = requests.post(
                    url, json=payload, timeout=settings.resolved_llm_timeout_seconds
                )
                response.raise_for_status()
                data = response.json()
                text = cast(str, data.get("message", {}).get("content", ""))
                pt = data.get("prompt_eval_count", 0) or 0
                ct = data.get("eval_count", 0) or 0
                return text, TokenUsage(prompt_tokens=pt, completion_tokens=ct, total_tokens=pt + ct, estimated_cost_usd=0.0)
            except Exception:
                return "", TokenUsage()

        try:
            return with_retry(
                _call,
                max_attempts=settings.retry_max_attempts,
                base_delay=settings.retry_base_delay_seconds,
                max_delay=settings.retry_max_delay_seconds,
                label="llm/ollama",
            )
        except Exception as e:
            logger.error(f"Ollama error: {e}")
            return "", TokenUsage()"""
code = re.sub(r"        def _call\(\) -> str:(.*?)(?=class LLMClient)", ollama_patch + "\n\n", code, flags=re.DOTALL, count=1)

with open("backend/clients/llm_client.py", "w") as f:
    f.write(code)
PY_EOF
python patch_llm_client.py

# 5. backend/agents/research_agent.py
cat << 'PY_EOF' > patch_research_agent.py
import re

with open("backend/agents/research_agent.py", "r") as f:
    code = f.read()

code = code.replace("from backend.utils.schemas import LLMResponseValidationError", "from backend.utils.schemas import LLMResponseValidationError, TokenUsage")
code = code.replace("def get_answer(self, prompt: str) -> str:", "def get_answer(self, prompt: str) -> tuple[str, \"TokenUsage\"]:")

code = code.replace(
    "def collect_item_with_confidence(\n        self, item_id: str, fields: list[str] | None = None\n    ) -> tuple[dict[str, str], dict[str, float | None]]:",
    "def collect_item_with_confidence(\n        self, item_id: str, fields: list[str] | None = None\n    ) -> tuple[dict[str, str], dict[str, float | None], TokenUsage]:"
)
code = code.replace(
    "def collect_item_with_confidence(self, item_id: str, fields: list[str] | None = None) -> tuple[dict[str, str], dict[str, float | None]]:",
    "def collect_item_with_confidence(self, item_id: str, fields: list[str] | None = None) -> tuple[dict[str, str], dict[str, float | None], TokenUsage]:"
)

patch1 = """        accumulated_usage = TokenUsage()

        if use_cache and cache_key:
            cached = get_cache("llm", cache_key)
            if cached:
                logger.info(f"LLM cache hit for {item_id}")
                try:
                    last_raw = cached
                    values, confidence = parse_answer_strict(last_raw, output_fields)
                    if values:
                        return self._finalize_values(values, search_results, output_fields), confidence, accumulated_usage
                except LLMResponseValidationError:
                    logger.warning(f"Cached LLM result for {item_id} is invalid; re-fetching.")

        last_raw = ""
        for attempt in range(settings.llm_validation_max_attempts):
            try:
                last_raw, attempt_usage = self.llm_client.get_answer(prompt)
                accumulated_usage = accumulated_usage + attempt_usage
                if not last_raw:"""
code = re.sub(r"        if use_cache and cache_key:.*?last_raw = self.llm_client.get_answer\(prompt\).*?if not last_raw:", patch1, code, flags=re.DOTALL)

patch2 = """                        if use_cache and cache_key:
                            set_cache("llm", cache_key, last_raw, ttl_days=settings.cache_llm_ttl_days)
                        return self._finalize_values(values, search_results, output_fields), confidence, accumulated_usage"""
code = re.sub(r"                        if use_cache and cache_key:\s+set_cache\(\"llm\", cache_key, last_raw, ttl_days=settings.cache_llm_ttl_days\)\s+return self\._finalize_values\(values, search_results, output_fields\), confidence", patch2, code, flags=re.DOTALL)

patch3 = """        fallback_values = parse_answer(last_raw, output_fields)
        return self._finalize_values(fallback_values, search_results, output_fields), {}, accumulated_usage"""
code = re.sub(r"        fallback_values = parse_answer\(last_raw, output_fields\)\s+return self\._finalize_values\(fallback_values, search_results, output_fields\), \{\}", patch3, code, flags=re.DOTALL)

patch4 = """    def collect_item(self, item_id: str, fields: list[str] | None = None) -> dict[str, str]:
        values, _, _usage = self.collect_item_with_confidence(item_id, fields)
        return values"""
code = re.sub(r"    def collect_item\(self, item_id: str, fields: list\[str\] \| None = None\) -> dict\[str, str\]:\s+values, _ = self\.collect_item_with_confidence\(item_id, fields\)\s+return values", patch4, code, flags=re.DOTALL)

with open("backend/agents/research_agent.py", "w") as f:
    f.write(code)
PY_EOF
python patch_research_agent.py

# 6. backend/utils/migrations.py
cat << 'PY_EOF' > patch_migrations.py
import sqlite3

with open("backend/utils/migrations.py", "r") as f:
    code = f.read()

patch = """
def add_job_token_accounting(cur: sqlite3.Cursor, _context: MigrationContext) -> None:
    cur.execute("ALTER TABLE jobs ADD COLUMN total_prompt_tokens INTEGER DEFAULT 0")
    cur.execute("ALTER TABLE jobs ADD COLUMN total_completion_tokens INTEGER DEFAULT 0")
    cur.execute("ALTER TABLE jobs ADD COLUMN total_llm_requests INTEGER DEFAULT 0")
    cur.execute("ALTER TABLE jobs ADD COLUMN estimated_cost_usd REAL DEFAULT 0.0")

def add_item_token_accounting(cur: sqlite3.Cursor, _context: MigrationContext) -> None:
    cur.execute("ALTER TABLE items ADD COLUMN prompt_tokens INTEGER DEFAULT 0")
    cur.execute("ALTER TABLE items ADD COLUMN completion_tokens INTEGER DEFAULT 0")
    cur.execute("ALTER TABLE items ADD COLUMN llm_requests INTEGER DEFAULT 1")
    cur.execute("ALTER TABLE items ADD COLUMN estimated_cost_usd REAL DEFAULT 0.0")

MIGRATIONS = [
"""

if "add_job_token_accounting" not in code:
    code = code.replace("MIGRATIONS = [", patch)

    migration_entries = """    Migration(8, "add_job_template_fields", add_job_template_fields),
    Migration(9, "add_job_token_accounting", add_job_token_accounting),
    Migration(10, "add_item_token_accounting", add_item_token_accounting),
]"""

    code = code.replace("    Migration(8, \"add_job_template_fields\", add_job_template_fields),\n]", migration_entries)

    with open("backend/utils/migrations.py", "w") as f:
        f.write(code)
PY_EOF
python patch_migrations.py

# 7. backend/utils/jobs.py
cat << 'PY_EOF' >> backend/utils/jobs.py

def update_job_token_usage(
    job_id: str,
    prompt_tokens: int,
    completion_tokens: int,
    cost_usd: float,
) -> None:
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            UPDATE jobs
            SET total_prompt_tokens    = total_prompt_tokens + ?,
                total_completion_tokens = total_completion_tokens + ?,
                total_llm_requests     = total_llm_requests + 1,
                estimated_cost_usd     = ROUND(estimated_cost_usd + ?, 8)
            WHERE job_id = ?
            """,
            (prompt_tokens, completion_tokens, cost_usd, job_id),
        )
        conn.commit()
    except Exception as e:
        logger.error(f"Error updating job {job_id} token usage: {e}")
    finally:
        conn.close()
PY_EOF

# 8. backend/utils/db_writer.py
cat << 'PY_EOF' > patch_db_writer.py
import re

with open("backend/utils/db_writer.py", "r") as f:
    code = f.read()

if "TokenUsage" not in code:
    code = code.replace("from backend.config import settings", "from backend.config import settings\nfrom backend.utils.schemas import TokenUsage")

code = code.replace(
    "def save_single_item(\n    item_id: str,\n    data: dict[str, Any],\n    output_fields: list[str],\n    run_id: int | None = None,\n    confidence: dict[str, float | None] | None = None,\n) -> None:",
    "def save_single_item(\n    item_id: str,\n    data: dict[str, Any],\n    output_fields: list[str],\n    run_id: int | None = None,\n    confidence: dict[str, float | None] | None = None,\n    token_usage: TokenUsage | None = None,\n) -> None:"
)
code = code.replace(
    "save_results_bulk([row_data], output_fields, run_id=run_id, confidence_list=conf_list)",
    "save_results_bulk(\n        [row_data],\n        output_fields,\n        run_id=run_id,\n        confidence_list=conf_list,\n        token_usage_list=[token_usage] if token_usage else None,\n    )"
)

code = code.replace(
    "def save_results_bulk(\n    data_list: list[tuple[str, ...]],\n    fields: list[str],\n    run_id: int | None = None,\n    confidence_list: list[dict[str, float | None]] | None = None,\n) -> None:",
    "def save_results_bulk(\n    data_list: list[tuple[str, ...]],\n    fields: list[str],\n    run_id: int | None = None,\n    confidence_list: list[dict[str, float | None]] | None = None,\n    token_usage_list: list[TokenUsage] | None = None,\n) -> None:"
)

update_code = """
            if token_usage_list and len(token_usage_list) > row_index and token_usage_list[row_index]:
                usage = token_usage_list[row_index]
                cur.execute(
                    "UPDATE items SET prompt_tokens = ?, completion_tokens = ?, llm_requests = 1, estimated_cost_usd = ? WHERE id = ?",
                    (usage.prompt_tokens, usage.completion_tokens, usage.estimated_cost_usd, db_item_id)
                )"""

code = re.sub(r"(db_item_id = cur\.lastrowid.*?)(?=\n\s+# Write values into normalized tables)", r"\1" + update_code, code, flags=re.DOTALL)

update_code2 = """
                if token_usage_list and len(token_usage_list) > row_index and token_usage_list[row_index]:
                    usage = token_usage_list[row_index]
                    cur.execute(
                        "UPDATE items SET prompt_tokens = ?, completion_tokens = ?, llm_requests = 1, estimated_cost_usd = ? WHERE id = ?",
                        (usage.prompt_tokens, usage.completion_tokens, usage.estimated_cost_usd, db_item_id)
                    )"""

code = re.sub(r"(db_item_id = cur\.fetchone\(\)\[0\])", r"\1" + update_code2, code)

with open("backend/utils/db_writer.py", "w") as f:
    f.write(code)
PY_EOF
python patch_db_writer.py

# 9. backend/main.py
cat << 'PY_EOF' > patch_main.py
import re

with open("backend/main.py", "r") as f:
    code = f.read()

code = code.replace(
    "from backend.utils.jobs import (\n    get_job,\n    update_job_progress,\n    update_job_status,\n    update_job_total_items,\n)",
    "from backend.utils.jobs import (\n    get_job,\n    update_job_progress,\n    update_job_status,\n    update_job_total_items,\n    update_job_token_usage,\n)\nfrom backend.utils.schemas import LLMResponseValidationError, TokenUsage"
)

code = code.replace(
    "    batch_confidence: list[dict[str, float | None]] = []\n    existing_ids",
    "    batch_confidence: list[dict[str, float | None]] = []\n    batch_token_usage: list[TokenUsage] = []\n    existing_ids"
)

patch = """            batch_usage = TokenUsage()

            for row in tqdm(batch_df.itertuples(), total=len(batch_df), desc="Processing batch"):
                item_id = str(row[col_idx])

                if item_id in existing_ids:
                    logger.debug(f"Skipping {item_id} — already in database")
                    skipped_in_batch += 1
                    continue

                if job_id:
                    current_job = get_job(job_id)
                    if current_job and current_job.get("status") == "cancelled":
                        logger.info(f"Job {job_id} was cancelled. Stopping item processing.")
                        return

                try:
                    parsed, conf, item_usage = agent.collect_item_with_confidence(item_id, output_fields)
                    batch_usage = batch_usage + item_usage
                    row_data = prepare_row_data(item_id, parsed, output_fields)
                    buffer.append(row_data)
                    batch_confidence.append(conf)
                    batch_token_usage.append(item_usage)
                    processed_in_batch += 1
                except LLMResponseValidationError as e:
                    logger.error(f"Validation error for item {item_id}: {e}")
                    failed_in_batch += 1
                except Exception as e:
                    logger.error(f"Error processing item {item_id}: {e}")
                    failed_in_batch += 1

            if buffer:
                save_results_bulk(
                    buffer,
                    output_fields,
                    run_id=current_run_id,
                    confidence_list=batch_confidence,
                    token_usage_list=batch_token_usage,
                )
                buffer = []
                batch_confidence = []
                batch_token_usage = []

            if job_id:
                update_job_progress(
                    job_id,
                    processed=processed_in_batch,
                    skipped=skipped_in_batch,
                    failed=failed_in_batch,
                )
                update_job_token_usage(
                    job_id,
                    batch_usage.prompt_tokens,
                    batch_usage.completion_tokens,
                    batch_usage.estimated_cost_usd,
                )"""

code = re.sub(r"            for row in tqdm\(batch_df.itertuples\(\), total=len\(batch_df\), desc=\"Processing batch\"\):.*?failed=failed_in_batch,\n                \)", patch, code, flags=re.DOTALL)

with open("backend/main.py", "w") as f:
    f.write(code)
PY_EOF
python patch_main.py

# 10. backend/api/routes.py
cat << 'PY_EOF' >> backend/api/routes.py

@router.get("/jobs/{job_id}/cost-report")
def get_job_cost_report(job_id: str) -> dict[str, Any]:
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    pt = job.get("total_prompt_tokens") or 0
    ct = job.get("total_completion_tokens") or 0
    return {
        "job_id": job_id,
        "status": job["status"],
        "total_prompt_tokens": pt,
        "total_completion_tokens": ct,
        "total_tokens": pt + ct,
        "total_llm_requests": job.get("total_llm_requests") or 0,
        "estimated_cost_usd": job.get("estimated_cost_usd") or 0.0,
        "model": settings.resolved_llm_model,
        "provider": settings.resolved_llm_provider,
    }
PY_EOF

# 11. Tests

cat << 'PY_EOF' > patch_tests_research_agent.py
import re

with open("tests/test_research_agent.py", "r") as f:
    code = f.read()

if "TokenUsage" not in code:
    code = code.replace("from backend.utils.schemas import LLMExtractionResponse", "from backend.utils.schemas import LLMExtractionResponse, TokenUsage")

patch_fake_client = """class FakeLLMClient:
    def __init__(self) -> None:
        self._responses: list[str] = []

    def set_responses(self, responses: list[str]) -> None:
        self._responses = list(responses)

    def get_answer(self, prompt: str) -> tuple[str, TokenUsage]:
        response = self._responses.pop(0) if self._responses else ""
        return response, TokenUsage()"""

code = re.sub(r"class FakeLLMClient:.*?(?=class FakeSearchTool:)", patch_fake_client + "\n\n\n", code, flags=re.DOTALL)

code = code.replace("values, conf = agent.collect_item_with_confidence(\"ITEM-123\", fields)", "values, conf, _ = agent.collect_item_with_confidence(\"ITEM-123\", fields)")
code = code.replace("values, confidence = agent.collect_item_with_confidence(\"ITEM-123\", [\"Weight\", \"Sources\"])", "values, confidence, _ = agent.collect_item_with_confidence(\"ITEM-123\", [\"Weight\", \"Sources\"])")

with open("tests/test_research_agent.py", "w") as f:
    f.write(code)
PY_EOF
python patch_tests_research_agent.py

cat << 'PY_EOF' > patch_tests_llm_cache.py
import re

with open("tests/test_llm_cache.py", "r") as f:
    code = f.read()

if "TokenUsage" not in code:
    code = code.replace("import pytest", "import pytest\nfrom backend.utils.schemas import TokenUsage")

patch_fake_client = """class FakeLLMClient:
    def __init__(self, answer: str) -> None:
        self.answer = answer
        self.call_count = 0

    def get_answer(self, prompt: str) -> tuple[str, TokenUsage]:
        self.call_count += 1
        return self.answer, TokenUsage()"""

code = re.sub(r"class FakeLLMClient:.*?return self\.answer", patch_fake_client, code, flags=re.DOTALL)

with open("tests/test_llm_cache.py", "w") as f:
    f.write(code)
PY_EOF
python patch_tests_llm_cache.py

cat << 'PY_EOF' > tests/test_token_usage.py
from backend.utils.schemas import TokenUsage
from backend.utils.pricing import estimate_cost, get_price_per_1k

def test_token_usage_defaults():
    tu = TokenUsage()
    assert tu.prompt_tokens == 0
    assert tu.completion_tokens == 0
    assert tu.total_tokens == 0
    assert tu.estimated_cost_usd == 0.0

def test_token_usage_addition():
    tu1 = TokenUsage(100, 50, 150, 0.001)
    tu2 = TokenUsage(200, 100, 300, 0.002)
    tu3 = tu1 + tu2
    assert tu3.prompt_tokens == 300
    assert tu3.completion_tokens == 150
    assert tu3.total_tokens == 450
    assert tu3.estimated_cost_usd == 0.003

def test_estimate_cost_known_model():
    cost = estimate_cost(1000, 500, "gpt-4o-mini")
    assert cost == 0.00045

def test_estimate_cost_unknown_model():
    cost = estimate_cost(0, 0, "totally-unknown-model-xyz")
    assert cost == 0.0

def test_get_price_per_1k():
    assert get_price_per_1k("deepseek-chat") == (0.000270, 0.001100)
    assert get_price_per_1k("MY-CUSTOM-GPT-4O-MINI-FINETUNED") == (0.000150, 0.000600)
PY_EOF

sed -i 's/update_job_status,/update_job_status, update_job_token_usage,/' tests/test_jobs.py
cat << 'PY_EOF' >> tests/test_jobs.py

def test_update_job_token_usage_accumulates(setup_test_db):
    job_id = "job-tokens-1"
    create_job(job_id, "input.xlsx", "output.xlsx")

    update_job_token_usage(job_id, 100, 50, 0.001)
    update_job_token_usage(job_id, 100, 50, 0.001)

    job = get_job(job_id)
    assert job["total_prompt_tokens"] == 200
    assert job["total_completion_tokens"] == 100
    assert job["total_llm_requests"] == 2
    assert job["estimated_cost_usd"] == 0.002

def test_get_job_includes_token_fields(setup_test_db):
    job_id = "job-tokens-2"
    create_job(job_id, "in.xlsx", "out.xlsx")
    update_job_token_usage(job_id, 500, 200, 0.01)

    job = get_job(job_id)
    assert "total_prompt_tokens" in job
    assert "total_completion_tokens" in job
    assert "total_llm_requests" in job
    assert "estimated_cost_usd" in job
    assert job["total_prompt_tokens"] == 500
    assert job["total_completion_tokens"] == 200
    assert job["total_llm_requests"] == 1
    assert job["estimated_cost_usd"] == 0.01
PY_EOF

cat << 'PY_EOF' >> tests/test_api.py

@pytest.fixture
def setup_test_db(tmp_path):
    import sqlite3
    from backend.config import settings
    from backend.utils.migrations import ensure_migration_table, run_migrations
    db_path = tmp_path / "test.sqlite"
    old_db_path = settings.db_path
    settings.db_path = str(db_path)

    conn = sqlite3.connect(settings.db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.cursor()
    ensure_migration_table(cur)
    run_migrations(conn, settings.column_name, settings.target_fields)
    conn.commit()
    conn.close()

    yield
    settings.db_path = old_db_path

def test_cost_report_unknown_job_returns_404():
    response = client.get("/jobs/nonexistent-id/cost-report")
    assert response.status_code == 404

def test_cost_report_new_job_returns_zero_counters(setup_test_db):
    from backend.utils.jobs import create_job
    job_id = "test-job-cost-report-zero"
    create_job(job_id, "test.xlsx", "out.xlsx")

    response = client.get(f"/jobs/{job_id}/cost-report")
    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == job_id
    assert data["total_prompt_tokens"] == 0
PY_EOF

cat << 'PY_EOF' > fix_test_db_writer.py
import re

with open("tests/test_db_writer.py", "r") as f:
    code = f.read()

code = code.replace(
    '(8, "add_job_template_fields"),\n    ]',
    '(8, "add_job_template_fields"),\n        (9, "add_job_token_accounting"),\n        (10, "add_item_token_accounting"),\n    ]'
)

code = code.replace(
    'assert migration_count == 8',
    'assert migration_count == 10'
)

with open("tests/test_db_writer.py", "w") as f:
    f.write(code)
PY_EOF
python fix_test_db_writer.py

# 12. Update Roadmap
cat << 'PY_EOF' > patch_roadmap.py
with open("ROADMAP.md", "r") as f:
    content = f.read()

content = content.replace("| 14 | **Cost/token accounting** — track tokens, estimated cost, request count, per-job pricing, exportable report                                                     | 🔲     |", "| 14 | **Cost/token accounting** — track tokens, estimated cost, request count, per-job pricing, exportable report                                                     | ✅     |")
content = content.replace("**Progress: 14 / 20 done**", "**Progress: 15 / 20 done**")

with open("ROADMAP.md", "w") as f:
    f.write(content)
PY_EOF
python patch_roadmap.py

# Cleanup
rm patch_*.py fix_*.py
