from __future__ import annotations

import io
import sys

from eq_cli import Application, create_app
from eq_cli.audio import AudioInputDevice, AudioInputDeviceProvider, SoundDeviceProvider
from eq_cli.cli import build_parser, main
from eq_cli.peaks import PeakTracker
from eq_cli.renderer import RenderFrame, TerminalRenderer, supports_color
from eq_cli.spectrum import (
    AudioFrame,
    SpectrumBands,
    SpectrumProcessor,
    build_log_frequency_centers,
    magnitude_to_db,
)


def test_package_imports_are_accessible() -> None:
    """All public symbols should be importable from a fresh install."""
    assert Application is not None
    assert create_app is not None
    assert main is not None
    assert build_parser is not None
    assert AudioInputDevice is not None
    assert AudioInputDeviceProvider is not None
    assert SoundDeviceProvider is not None
    assert PeakTracker is not None
    assert RenderFrame is not None
    assert TerminalRenderer is not None
    assert supports_color is not None
    assert AudioFrame is not None
    assert SpectrumBands is not None
    assert SpectrumProcessor is not None
    assert build_log_frequency_centers is not None
    assert magnitude_to_db is not None


def test_cli_entrypoint_help_is_reachable() -> None:
    """The CLI entrypoint should exit cleanly when invoked with --help."""
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()

    try:
        exit_code = main(["--help"])
    except SystemExit as exc:
        exit_code = exc.code if isinstance(exc.code, int) else 0
    finally:
        sys.stdout = old_stdout

    assert exit_code == 0
