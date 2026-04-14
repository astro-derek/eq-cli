from __future__ import annotations

import json
from pathlib import Path

import pytest

from eq_cli.profile import list_builtin_profiles, load_profile, resolve_color_code


def test_list_builtin_profiles_exposes_expected_presets() -> None:
    """Built-in profile names should be discoverable for CLI/help/docs use."""
    assert list_builtin_profiles() == (
        "default",
        "green-based",
        "high-contrast",
        "minimal",
        "studio",
    )


def test_load_profile_reads_builtin_profile_without_file() -> None:
    """Built-in profiles should be available without specifying a profile file."""
    profile = load_profile(None, "studio")

    assert profile["title_text"] == "eq-cli studio"
    assert profile["db_marker_style"] == "minimal"
    assert profile["volume_mode"] == "absolute"
    assert profile["peak_hold_frames"] == 12
    assert profile["channel_mode"] == "sum"
    assert profile["show_shortcuts"] is True
    assert profile["history_rows"] == 0
    assert profile["history_gradient"] == " .:-=+*#%@"
    assert profile["db_min"] == -76.0
    assert profile["db_max"] == 0.0
    assert profile["graph_height"] == 24
    assert profile["graph_width"] == 140
    assert profile["peak_char"] == "_"
    assert profile["snapshot_format"] == "ansi"
    assert profile["snapshot_dir"] == "snapshots"


def test_load_profile_reads_green_based_builtin_profile() -> None:
    """Green-based built-in profile should expose green-focused color settings."""
    profile = load_profile(None, "green-based")

    assert profile["title_text"] == "eq-cli green-based"
    assert profile["colors"]["bar"] == "green"
    assert profile["colors"]["history"] == "bright_green"


def test_load_profile_reads_named_profile(tmp_path: Path) -> None:
    """Profile loader should return the selected profile object."""
    profile_path = tmp_path / "profiles.json"
    profile_path.write_text(
        json.dumps(
            {
                "profiles": {
                    "ocean": {
                        "gain": 3.5,
                        "volume_mode": "absolute",
                        "refresh_rate": 45.0,
                        "block_size": 2048,
                        "graph_height": 12,
                        "axis_frequencies": [50.0, 100.0, 1000.0, 5000.0],
                        "snapshot_format": "ansi",
                        "snapshot_dir": "captures",
                        "snapshot_file": "captures/current.txt",
                        "peak_db_labels": True,
                        "bar_char": "=",
                        "colors": {"bar": "cyan", "peak": "red"},
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    profile = load_profile(str(profile_path), "ocean")

    assert profile["bar_char"] == "="
    assert profile["gain"] == 3.5
    assert profile["graph_height"] == 12
    assert profile["volume_mode"] == "absolute"
    assert profile["refresh_rate"] == 45.0
    assert profile["block_size"] == 2048
    assert profile["axis_frequencies"] == (50.0, 100.0, 1000.0, 5000.0)
    assert profile["snapshot_format"] == "ansi"
    assert profile["snapshot_dir"] == "captures"
    assert profile["snapshot_file"] == "captures/current.txt"
    assert profile["peak_db_labels"] is True


def test_load_profile_raises_for_unknown_profile(tmp_path: Path) -> None:
    """Profile loader should fail when requested profile does not exist."""
    profile_path = tmp_path / "profiles.json"
    profile_path.write_text(json.dumps({"profiles": {"default": {}}}), encoding="utf-8")

    with pytest.raises(ValueError, match="Unknown profile"):
        load_profile(str(profile_path), "missing")


def test_load_profile_raises_for_unknown_builtin_profile() -> None:
    """Built-in profile lookup should surface available preset names."""
    with pytest.raises(ValueError, match="Unknown built-in profile"):
        load_profile(None, "missing")


def test_load_profile_rejects_unsupported_field(tmp_path: Path) -> None:
    """Schema validation should reject unknown profile fields clearly."""
    profile_path = tmp_path / "profiles.json"
    profile_path.write_text(
        json.dumps({"profiles": {"broken": {"unknown_field": 1}}}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="unknown_field"):
        load_profile(str(profile_path), "broken")


def test_load_profile_rejects_invalid_color_value(tmp_path: Path) -> None:
    """Schema validation should point to the specific invalid color field."""
    profile_path = tmp_path / "profiles.json"
    profile_path.write_text(
        json.dumps(
            {
                "profiles": {
                    "broken": {"colors": {"bar": "not-a-color"}}
                }
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match=r"colors'.*bar.*Unsupported color"):
        load_profile(str(profile_path), "broken")


def test_load_profile_accepts_history_color_key(tmp_path: Path) -> None:
    """Profile colors should support a dedicated history color key."""
    profile_path = tmp_path / "profiles.json"
    profile_path.write_text(
        json.dumps(
            {
                "profiles": {
                    "custom": {
                        "colors": {"history": "yellow"}
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    profile = load_profile(str(profile_path), "custom")

    assert profile["colors"]["history"] == "yellow"


def test_load_profile_rejects_invalid_marker_style(tmp_path: Path) -> None:
    """Schema validation should reject unsupported marker styles."""
    profile_path = tmp_path / "profiles.json"
    profile_path.write_text(
        json.dumps(
            {"profiles": {"broken": {"db_marker_style": "dense"}}}
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="all, spaced, minimal"):
        load_profile(str(profile_path), "broken")


def test_load_profile_rejects_invalid_snapshot_format(tmp_path: Path) -> None:
    """Profile validation should reject unsupported snapshot formats."""
    profile_path = tmp_path / "profiles.json"
    profile_path.write_text(
        json.dumps(
            {"profiles": {"broken": {"snapshot_format": "html"}}}
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="txt, ansi"):
        load_profile(str(profile_path), "broken")


def test_load_profile_rejects_invalid_axis_frequencies(tmp_path: Path) -> None:
    """Profile validation should reject non-positive axis frequency values."""
    profile_path = tmp_path / "profiles.json"
    profile_path.write_text(
        json.dumps(
            {"profiles": {"broken": {"axis_frequencies": [50.0, 0.0, 1000.0]}}}
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="greater than zero"):
        load_profile(str(profile_path), "broken")


def test_load_profile_rejects_invalid_volume_mode(tmp_path: Path) -> None:
    """Schema validation should reject unsupported volume modes."""
    profile_path = tmp_path / "profiles.json"
    profile_path.write_text(
        json.dumps({"profiles": {"broken": {"volume_mode": "boosted"}}}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="relative, absolute"):
        load_profile(str(profile_path), "broken")


def test_load_profile_rejects_negative_peak_hold_frames(tmp_path: Path) -> None:
    """Profile validation should reject negative peak hold frame values."""
    profile_path = tmp_path / "profiles.json"
    profile_path.write_text(
        json.dumps({"profiles": {"broken": {"peak_hold_frames": -1}}}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="zero or greater"):
        load_profile(str(profile_path), "broken")


def test_load_profile_accepts_zero_graph_height_for_auto_mode(tmp_path: Path) -> None:
    """Profile validation should allow zero graph height to preserve auto mode."""
    profile_path = tmp_path / "profiles.json"
    profile_path.write_text(
        json.dumps({"profiles": {"custom": {"graph_height": 0}}}),
        encoding="utf-8",
    )

    profile = load_profile(str(profile_path), "custom")

    assert profile["graph_height"] == 0


def test_load_profile_rejects_invalid_channel_mode(tmp_path: Path) -> None:
    """Profile validation should reject unsupported channel modes."""
    profile_path = tmp_path / "profiles.json"
    profile_path.write_text(
        json.dumps({"profiles": {"broken": {"channel_mode": "surround"}}}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="mono, left, right, sum, mid, side"):
        load_profile(str(profile_path), "broken")


def test_load_profile_rejects_empty_history_gradient(tmp_path: Path) -> None:
    """Profile validation should reject empty history gradient strings."""
    profile_path = tmp_path / "profiles.json"
    profile_path.write_text(
        json.dumps({"profiles": {"broken": {"history_gradient": ""}}}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="must not be empty"):
        load_profile(str(profile_path), "broken")


def test_resolve_color_code_accepts_names_and_numeric_codes() -> None:
    """Color resolver should support named and numeric ANSI values."""
    assert resolve_color_code("cyan") == "\x1b[36m"
    assert resolve_color_code("31") == "\x1b[31m"


def test_resolve_color_code_rejects_unsupported_values() -> None:
    """Color resolver should reject unknown color values."""
    with pytest.raises(ValueError, match="Unsupported color value"):
        resolve_color_code("not-a-color")