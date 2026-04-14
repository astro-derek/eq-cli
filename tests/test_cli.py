from __future__ import annotations

from pathlib import Path

import pytest

from eq_cli.app import create_app
from eq_cli.cli import build_parser, main


def test_build_parser_help_exits_successfully() -> None:
    """The CLI parser should exit cleanly when help is requested."""
    parser = build_parser()

    with pytest.raises(SystemExit) as exc_info:
        parser.parse_args(["--help"])

    assert exc_info.value.code == 0


def test_main_returns_success_for_help(capsys: pytest.CaptureFixture[str]) -> None:
    """The CLI entrypoint should return success for --help."""
    exit_code = main(["--help"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "usage:" in captured.out
    assert "Capture live audio from an input device" in captured.out
    assert "Usability Tips:" in captured.out
    assert (
        "Runtime keys: f=freeze, r=reset peaks, s=snapshot, "
        "p=export profile, q=quit" in captured.out
    )


def test_create_app_returns_named_application() -> None:
    """Application factory should provide a stable application definition."""
    app = create_app()

    assert app.name == "eq-cli"


def test_build_parser_accepts_refresh_rate_option() -> None:
    """Parser should accept and parse the refresh-rate option."""
    parser = build_parser()

    args = parser.parse_args(["--refresh-rate", "60"])

    assert args.refresh_rate == 60.0


def test_build_parser_accepts_profile_selection_options() -> None:
    """Parser should accept profile file and profile name arguments."""
    parser = build_parser()

    args = parser.parse_args(
        [
            "--profile-file",
            "profiles/theme_profiles.json",
            "--profile",
            "ocean",
        ]
    )

    assert args.profile_file == "profiles/theme_profiles.json"
    assert args.profile == "ocean"


def test_build_parser_axis_labels_are_opt_in() -> None:
    """Axis labels should be disabled by default and enabled via flag."""
    parser = build_parser()

    default_args = parser.parse_args([])
    enabled_args = parser.parse_args(["--axis-labels"])

    assert default_args.axis_labels is False
    assert enabled_args.axis_labels is True


def test_build_parser_supports_title_toggle() -> None:
    """Title should be enabled by default and disable-able via flag."""
    parser = build_parser()

    default_args = parser.parse_args([])
    hidden_args = parser.parse_args(["--no-title"])

    assert default_args.title is True
    assert hidden_args.title is False


def test_build_parser_accepts_db_marker_style() -> None:
    """Parser should accept db marker style choices."""
    parser = build_parser()

    args = parser.parse_args(["--db-marker-style", "minimal"])

    assert args.db_marker_style == "minimal"


def test_build_parser_accepts_list_profiles_option() -> None:
    """Parser should accept the list-profiles option."""
    parser = build_parser()

    args = parser.parse_args(["--list-profiles"])

    assert args.list_profiles is True


def test_build_parser_accepts_peak_hold_frames_option() -> None:
    """Parser should accept and parse peak-hold-frames."""
    parser = build_parser()

    args = parser.parse_args(["--peak-hold-frames", "12"])

    assert args.peak_hold_frames == 12


def test_build_parser_accepts_mode_option() -> None:
    """Parser should accept mode presets."""
    parser = build_parser()

    args = parser.parse_args(["--mode", "studio"])

    assert args.mode == "studio"


def test_build_parser_accepts_channel_mode_option() -> None:
    """Parser should accept stereo analysis channel modes."""
    parser = build_parser()

    args = parser.parse_args(["--channel-mode", "side"])

    assert args.channel_mode == "side"


def test_build_parser_shortcuts_are_enabled_by_default() -> None:
    """Runtime shortcuts legend should be enabled unless explicitly disabled."""
    parser = build_parser()

    default_args = parser.parse_args([])
    hidden_args = parser.parse_args(["--no-shortcuts"])

    assert default_args.show_shortcuts is True
    assert hidden_args.show_shortcuts is False


def test_build_parser_accepts_history_rows_option() -> None:
    """Parser should accept and parse history row count."""
    parser = build_parser()

    args = parser.parse_args(["--history-rows", "8"])

    assert args.history_rows == 8


def test_build_parser_accepts_graph_height_option() -> None:
    """Parser should accept and parse explicit graph height."""
    parser = build_parser()

    args = parser.parse_args(["--graph-height", "12"])

    assert args.graph_height == 12


def test_build_parser_accepts_history_gradient_option() -> None:
    """Parser should accept and parse custom history gradient text."""
    parser = build_parser()

    args = parser.parse_args(["--history-gradient", ".:=#"])

    assert args.history_gradient == ".:=#"


def test_build_parser_accepts_axis_frequencies_option() -> None:
    """Parser should accept and normalize custom axis frequency labels."""
    parser = build_parser()

    args = parser.parse_args(["--axis-frequencies", "50, 100,1000,5000"])

    assert args.axis_frequencies == (50.0, 100.0, 1000.0, 5000.0)


def test_build_parser_accepts_block_size_option() -> None:
    """Parser should accept and parse an explicit audio block size."""
    parser = build_parser()

    args = parser.parse_args(["--block-size", "2048"])

    assert args.block_size == 2048


def test_build_parser_accepts_snapshot_options() -> None:
    """Parser should accept snapshot file, format, and directory options."""
    parser = build_parser()

    args = parser.parse_args(
        [
            "--snapshot-file",
            "snapshots/frame.txt",
            "--snapshot-format",
            "ansi",
            "--snapshot-dir",
            "snapshots",
        ]
    )

    assert args.snapshot_file == "snapshots/frame.txt"
    assert args.snapshot_format == "ansi"
    assert args.snapshot_dir == "snapshots"


def test_build_parser_accepts_peak_db_label_options() -> None:
    """Parser should support enabling and disabling peak dB labels."""
    parser = build_parser()

    enabled_args = parser.parse_args(["--peak-db-labels"])
    disabled_args = parser.parse_args(["--no-peak-db-labels"])

    assert enabled_args.peak_db_labels is True
    assert disabled_args.peak_db_labels is False


def test_build_parser_accepts_history_color_option() -> None:
    """Parser should accept history color override option."""
    parser = build_parser()

    args = parser.parse_args(["--color-history", "yellow"])

    assert args.color_history == "yellow"


def test_main_rejects_negative_peak_hold_frames(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """CLI should reject negative peak hold frame values."""
    exit_code = main(["--peak-hold-frames", "-1"])

    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Peak hold frames must be zero or greater." in captured.err


def test_main_rejects_non_positive_graph_height(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """CLI should reject graph heights less than one row."""
    exit_code = main(["--graph-height", "0"])

    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Graph height must be greater than zero." in captured.err


def test_main_rejects_non_positive_block_size(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """CLI should reject non-positive explicit block sizes."""
    exit_code = main(["--block-size", "0"])

    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Block size must be greater than zero." in captured.err


# ---------------------------------------------------------------------------
# C2: block_size=None must not appear in exported profile JSON
# ---------------------------------------------------------------------------


def test_build_export_profile_omits_block_size_when_not_set(
    tmp_path: Path,
) -> None:
    """Exported profile must omit block_size when --block-size was not provided.

    Exporting a profile that contains 'block_size: null' causes a ValueError
    on re-import because the profile validator requires an integer.  This test
    confirms the key is absent entirely when the user has not set --block-size.
    """
    from eq_cli.cli import _build_export_profile
    from eq_cli.loop import _save_profile_export
    from eq_cli.profile import load_profile

    parser = build_parser()
    args = parser.parse_args([])

    profile = _build_export_profile(args, "eq-cli test")

    assert "block_size" not in profile, (
        "block_size must not be present in the profile when it was not set by the user"
    )

    # Round-trip: saving then reloading the profile must not raise.
    saved = _save_profile_export(profile, export_dir=str(tmp_path))
    reloaded = load_profile(str(saved), saved.stem)
    assert "block_size" not in reloaded


def test_build_export_profile_includes_block_size_when_set(
    tmp_path: Path,
) -> None:
    """Exported profile must include block_size when --block-size was provided."""
    from eq_cli.cli import _build_export_profile
    from eq_cli.loop import _save_profile_export
    from eq_cli.profile import load_profile

    parser = build_parser()
    args = parser.parse_args(["--block-size", "2048"])

    profile = _build_export_profile(args, "eq-cli test")

    assert profile.get("block_size") == 2048

    saved = _save_profile_export(profile, export_dir=str(tmp_path))
    reloaded = load_profile(str(saved), saved.stem)
    assert reloaded["block_size"] == 2048


# ---------------------------------------------------------------------------
# C3: --db-interval 0 must be rejected with a clear error message
# ---------------------------------------------------------------------------


def test_main_rejects_zero_db_interval(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """CLI should reject a db_interval of zero to prevent ZeroDivisionError."""
    exit_code = main(["--db-interval", "0"])

    captured = capsys.readouterr()

    assert exit_code == 1
    assert "dB interval must be greater than zero." in captured.err


def test_main_rejects_negative_db_interval(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """CLI should reject negative db_interval values."""
    exit_code = main(["--db-interval", "-5"])

    captured = capsys.readouterr()

    assert exit_code == 1
    assert "dB interval must be greater than zero." in captured.err


# ---------------------------------------------------------------------------
# M3: db_min >= db_max cross-parameter validation
# ---------------------------------------------------------------------------


def test_main_rejects_db_min_equal_to_db_max(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """CLI should reject configurations where db_min equals db_max."""
    exit_code = main(["--db-min", "0", "--db-max", "0"])

    captured = capsys.readouterr()

    assert exit_code == 1
    assert "--db-min must be less than --db-max." in captured.err


def test_main_rejects_db_min_greater_than_db_max(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """CLI should reject configurations where db_min exceeds db_max."""
    exit_code = main(["--db-min", "0", "--db-max", "-10"])

    captured = capsys.readouterr()

    assert exit_code == 1
    assert "--db-min must be less than --db-max." in captured.err
