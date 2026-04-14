from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import numpy as np

from eq_cli.loop import (
    _read_hotkey,
    _restore_posix_terminal,
    _save_posix_terminal,
    extract_channel_samples,
    interpret_hotkey,
)


def test_interpret_hotkey_maps_expected_actions() -> None:
    """Hotkey mapping should handle toggle, reset, and quit controls."""
    assert interpret_hotkey("f") == "toggle_freeze"
    assert interpret_hotkey("F") == "toggle_freeze"
    assert interpret_hotkey("r") == "reset_peaks"
    assert interpret_hotkey("q") == "quit"


def test_interpret_hotkey_ignores_unknown_or_missing_keys() -> None:
    """Unknown or absent key presses should produce no action."""
    assert interpret_hotkey(None) == "none"
    assert interpret_hotkey("x") == "none"


def test_extract_channel_samples_supports_stereo_modes() -> None:
    """Stereo channel extraction should map each supported mode correctly."""
    stereo = np.array([[1.0, -1.0], [0.5, -0.5]], dtype=np.float32)

    left = extract_channel_samples(stereo, "left")
    right = extract_channel_samples(stereo, "right")
    summed = extract_channel_samples(stereo, "sum")
    mid = extract_channel_samples(stereo, "mid")
    side = extract_channel_samples(stereo, "side")

    assert np.allclose(left, np.array([1.0, 0.5]))
    assert np.allclose(right, np.array([-1.0, -0.5]))
    assert np.allclose(summed, np.array([0.0, 0.0]))
    assert np.allclose(mid, np.array([0.0, 0.0]))
    assert np.allclose(side, np.array([1.0, 0.5]))


def test_extract_channel_samples_rejects_stereo_modes_for_mono_input() -> None:
    """Stereo-only modes should fail on single-channel buffers."""
    mono = np.array([[0.1], [0.2]], dtype=np.float32)

    try:
        extract_channel_samples(mono, "right")
        raised = False
    except ValueError:
        raised = True

    assert raised is True


def test_save_posix_terminal_noop_on_windows() -> None:
    """Terminal save should return None on Windows."""
    with patch("eq_cli.loop.os") as mock_os:
        mock_os.name = "nt"
        result = _save_posix_terminal()

    assert result is None


def test_save_posix_terminal_noop_when_not_a_tty() -> None:
    """Terminal save should return None when stdin is not a tty."""
    with patch("eq_cli.loop.os") as mock_os, patch.object(
        sys.stdin, "isatty", return_value=False
    ):
        mock_os.name = "posix"
        result = _save_posix_terminal()

    assert result is None


def test_restore_posix_terminal_noop_when_none() -> None:
    """Restoring None saved state should not raise and not call tcsetattr."""
    with patch.dict("sys.modules", {"termios": MagicMock()}) as _:
        _restore_posix_terminal(None)  # must not raise


def test_read_hotkey_returns_none_when_not_a_tty() -> None:
    """Hotkey reader should return None for non-tty stdin on any platform."""
    with patch.object(sys.stdin, "isatty", return_value=False):
        result = _read_hotkey()

    assert result is None


def test_read_hotkey_posix_returns_none_when_no_data() -> None:
    """POSIX hotkey reader should return None when no key is available."""
    with (
        patch("eq_cli.loop.os") as mock_os,
        patch.object(sys.stdin, "isatty", return_value=True),
        patch("eq_cli.loop.select") as mock_select,
    ):
        mock_os.name = "posix"
        mock_select.select.return_value = ([], [], [])

        result = _read_hotkey()

    assert result is None


def test_read_hotkey_posix_returns_key_when_data_available() -> None:
    """POSIX hotkey reader should return the character when stdin has data."""
    with (
        patch("eq_cli.loop.os") as mock_os,
        patch.object(sys.stdin, "isatty", return_value=True),
        patch("eq_cli.loop.select") as mock_select,
        patch.object(sys.stdin, "read", return_value="f"),
    ):
        mock_os.name = "posix"
        mock_select.select.return_value = ([sys.stdin], [], [])

        result = _read_hotkey()

    assert result == "f"