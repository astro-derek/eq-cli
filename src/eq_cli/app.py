from __future__ import annotations

from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version

from eq_cli.config import AppConfig


@dataclass(frozen=True)
class Application:
    """Represents the current application metadata."""

    name: str
    description: str
    version: str


def get_app_version(package_name: str = "eq-cli") -> str:
    """Resolve the installed package version with a safe fallback."""
    try:
        return version(package_name)
    except PackageNotFoundError:
        return "0.0.0"


def create_app(config: AppConfig | None = None) -> Application:
    """Create the application definition used by the CLI.

    Args:
        config: Optional application configuration.

    Returns:
        Application metadata for the current process.
    """
    effective_config = config or AppConfig()
    return Application(
        name=effective_config.app_name,
        description=effective_config.description,
        version=get_app_version(),
    )
