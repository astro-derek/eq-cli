from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AppConfig:
    """Static configuration for the CLI application."""

    app_name: str = "eq-cli"
    description: str = "Real-time terminal equalizer"
