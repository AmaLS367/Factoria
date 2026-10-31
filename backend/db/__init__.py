"""Database initialization and schema migration entry points."""

from importlib import import_module
from typing import Any

__all__ = [
    "ensure_alembic_initialized",
    "get_alembic_config",
    "get_sqlite_url",
    "run_alembic_migrations",
]


def __getattr__(name: str) -> Any:
    """Resolve a public database helper lazily.

    Lazy loading avoids importing the Alembic runner while it is importing this package.

    Args:
        name: Public helper name requested from this package.

    Returns:
        The helper from ``alembic_runner``.

    Raises:
        AttributeError: If the name is not a public export.
    """
    if name not in __all__:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(".alembic_runner", __name__), name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """List package attributes, including lazy database helper exports.

    Returns:
        Sorted names available from this package.
    """
    return sorted(set(globals()) | set(__all__))
