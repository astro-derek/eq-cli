from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from eq_cli.loop import (
    _read_hotkey,
    _restore_posix_terminal,
    _save_posix_terminal,
    _save_profile_export,
    _save_snapshot,
    extract_channel_samples,
    interpret_hotkey,
)
from eq_cli.profile import load_profile
from eq_cli.renderer import RenderFrame, TerminalRenderer
from eq_cli.spectrum import build_log_frequency_centers


def test_interpret_hotkey_maps_expected_actions() -> None:
    """Hotkey mapping should handle toggle, reset, and quit controls."""
    assert interpret_hotkey("f") == "toggle_freeze"
    assert interpret_hotkey("F") == "toggle_freeze"
    assert interpret_hotkey("r") == "reset_peaks"
    assert interpret_hotkey("s") == "snapshot"
    assert interpret_hotkey("p") == "export_profile"
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


def test_save_snapshot_writes_plain_text_without_ansi(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Plain-text snapshots should strip ANSI color codes from saved output."""
    renderer = TerminalRenderer(color_enabled=True, show_axis_labels=True)
    frame = RenderFrame(
        frequencies_hz=tuple(build_log_frequency_centers(20.0, 20_000.0, 32)),
        levels_db=tuple([0.0] * 32),
    )
    monkeypatch.setattr("eq_cli.loop.time.strftime", lambda _fmt: "20260414-120000")

    snapshot_path = _save_snapshot(
        renderer=renderer,
        frame=frame,
        snapshot_format="txt",
        snapshot_file=None,
        snapshot_dir=str(tmp_path),
        title_text="eq-cli studio",
    )

    content = snapshot_path.read_text(encoding="utf-8")

    assert snapshot_path.name == "eq-cli-snapshot-20260414-120000-eq-cli-studio.txt"
    assert "\x1b[" not in content


def test_save_snapshot_uses_explicit_file_path(tmp_path) -> None:
    """Explicit snapshot file should win over auto-generated naming."""
    renderer = TerminalRenderer(color_enabled=False, show_title=False)
    frame = RenderFrame(
        frequencies_hz=tuple(build_log_frequency_centers(20.0, 20_000.0, 32)),
        levels_db=tuple([0.0] * 32),
        freeze_enabled=True,
    )
    snapshot_file = tmp_path / "captures" / "current.ansi"

    snapshot_path = _save_snapshot(
        renderer=renderer,
        frame=frame,
        snapshot_format="ansi",
        snapshot_file=str(snapshot_file),
        snapshot_dir=None,
        title_text="eq-cli studio",
    )

    assert snapshot_path == snapshot_file
    assert snapshot_path.exists()


def test_save_profile_export_uses_incrementing_file_names(tmp_path) -> None:
    """Profile exports should use the next numbered filename in the target folder."""
    (tmp_path / "eq-cli-profile-001.json").write_text("{}", encoding="utf-8")
    (tmp_path / "eq-cli-profile-002.json").write_text("{}", encoding="utf-8")

    export_path = _save_profile_export(
        {
            "gain": 3.5,
            "graph_height": 24,
            "graph_width": 140,
            "refresh_rate": 45.0,
            "block_size": 2048,
            "axis_frequencies": (50.0, 100.0, 1000.0, 5000.0),
            "peak_db_labels": True,
            "snapshot_file": "captures/current.txt",
            "snapshot_format": "ansi",
        },
        export_dir=str(tmp_path),
    )

    loaded_profile = load_profile(str(export_path), export_path.stem)

    assert export_path.name == "eq-cli-profile-003.json"
    assert loaded_profile["gain"] == 3.5
    assert loaded_profile["graph_height"] == 24
    assert loaded_profile["refresh_rate"] == 45.0
    assert loaded_profile["block_size"] == 2048
    assert loaded_profile["axis_frequencies"] == (50.0, 100.0, 1000.0, 5000.0)
    assert loaded_profile["peak_db_labels"] is True
    assert loaded_profile["snapshot_file"] == "captures/current.txt"
    assert loaded_profile["snapshot_format"] == "ansi"

# ---------------------------------------------------------------------------
# m4: TOCTOU-safe _save_profile_export
# ---------------------------------------------------------------------------


def test_save_profile_export_does_not_overwrite_existing_file(
    tmp_path: Path,
) -> None:
    """Concurrent atomic creates must not clobber each other's files."""
    # Simulate two concurrent writers by pre-creating slot 001 with known content.
    slot1 = tmp_path / "eq-cli-profile-001.json"
    slot1.write_text(
        '{"profiles":{"eq-cli-profile-001":{"gain":99}}}', encoding="utf-8"
    )

    # A second writer must claim slot 002 instead of overwriting slot 001.
    path = _save_profile_export({"gain": 1.0}, export_dir=str(tmp_path))
    assert path.name == "eq-cli-profile-002.json"

    # Original file is intact.
    assert slot1.read_text(encoding="utf-8").startswith('{"profiles"')


def test_save_profile_export_no_longer_exposes_next_profile_export_path() -> None:
    """_next_profile_export_path should have been removed (logic is now inlined)."""
    import eq_cli.loop as loop_module

    assert not hasattr(loop_module, "_next_profile_export_path"), (
        "_next_profile_export_path should not exist; use _save_profile_export directly"
    )
