"""Shared persistence, parsing, caching, pricing, and review utilities."""

from importlib import import_module
from typing import Any

_EXPORTS = {
    "BUILTIN_TEMPLATES": "templates",
    "LLMExtractionResponse": "schemas",
    "LLMResponseValidationError": "schemas",
    "Migration": "migrations",
    "MigrationContext": "migrations",
    "SOURCES_FIELD_NAME": "db_writer",
    "TRUSTED_DOMAINS": "credibility",
    "Template": "templates",
    "TokenUsage": "schemas",
    "cancel_job": "jobs",
    "create_job": "jobs",
    "create_run": "db_writer",
    "delete_template": "templates",
    "determine_review_status": "db_writer",
    "estimate_cost": "pricing",
    "fetch_all": "db_writer",
    "fetch_review_queue": "db_writer",
    "get_all_existing_ids": "db_writer",
    "get_cache": "cache",
    "get_db_path": "db_writer",
    "get_job": "jobs",
    "get_price_per_1k": "pricing",
    "get_recent_jobs": "jobs",
    "get_review_summary": "db_writer",
    "get_template": "templates",
    "init_db": "db_writer",
    "list_templates": "templates",
    "list_columns": "check_columns",
    "list_tables": "check_columns",
    "make_cache_key": "cache",
    "parse_answer": "parse",
    "parse_answer_strict": "parse",
    "prepare_row_data": "db_writer",
    "quote_identifier": "check_columns",
    "run_migrations": "migrations",
    "schema_lines": "check_columns",
    "save_results_bulk": "db_writer",
    "save_single_item": "db_writer",
    "save_template": "templates",
    "score_source": "credibility",
    "show_columns": "check_columns",
    "set_cache": "cache",
    "update_field_review": "db_writer",
    "update_job_progress": "jobs",
    "update_job_status": "jobs",
    "update_job_token_usage": "jobs",
    "update_job_total_items": "jobs",
    "with_retry": "retry",
}

__all__ = sorted(_EXPORTS)


def __getattr__(name: str) -> Any:
    """Import and return a public utility on first access.

    Lazy imports keep package-level re-exports from creating cycles between persistence,
    cache, and job modules.

    Args:
        name: Public utility name requested from this package.

    Returns:
        The named object from its defining utility module.

    Raises:
        AttributeError: If the name is not listed as a public export.
    """
    module_name = _EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(f".{module_name}", __name__), name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """List package attributes, including lazily loaded public exports.

    Returns:
        Sorted names available from this package.
    """
    return sorted(set(globals()) | set(__all__))
