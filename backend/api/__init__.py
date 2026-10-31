"""FastAPI application and route package for the data collection service."""

from importlib import import_module
from typing import Any

__all__ = ["app", "router"]


def __getattr__(name: str) -> Any:
    """Load the ASGI app or router only when it is requested.

    Args:
        name: Exported attribute name.

    Returns:
        The FastAPI app or route router.

    Raises:
        AttributeError: If the name is not a public export of this package.
    """
    if name == "app":
        value = import_module(".app", __name__).app
    elif name == "router":
        value = import_module(".routes", __name__).router
    else:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """List package attributes, including lazily loaded public exports.

    Returns:
        Sorted names available from this package.
    """
    return sorted(set(globals()) | set(__all__))
