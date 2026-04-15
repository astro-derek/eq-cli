from __future__ import annotations

import numpy as np
import pytest

import eq_cli.renderer as renderer_module
from eq_cli.renderer import (
    _LAYOUT_CACHE_MAX_SIZE,
    RenderFrame,
    TerminalRenderer,
    supports_color,
)
from eq_cli.spectrum import (
    _FRAME_CACHE_MAX_SIZE,
    DB_FLOOR,
    AudioFrame,
    SpectrumProcessor,
    build_log_frequency_centers,
)


def build_render_frame() -> RenderFrame:
    """Create a deterministic render frame for terminal renderer tests."""
    frequencies = tuple(build_log_frequency_centers(20.0, 20_000.0, 32))
    levels = tuple(max(DB_FLOOR, -float(index) * 2.0) for index in range(32))
    return RenderFrame(frequencies_hz=frequencies, levels_db=levels)


def test_render_frame_includes_frequency_and_db_axes() -> None:
    """Rendered output should include dB and frequency axis labels."""
    renderer = TerminalRenderer(color_enabled=False, show_axis_labels=True)

    output = renderer.render(build_render_frame())

    assert "6 dB +" in output
    assert "0 dB +" in output
    assert "-80 dB +" in output
    assert "20" in output
    assert "100" in output
    assert "1k" in output
    assert "10k" in output
    assert "20kHz" in output


def test_render_frame_supports_configurable_db_scale() -> None:
    """Renderer should honor caller-provided dB min/max/interval values."""
    renderer = TerminalRenderer(
        color_enabled=False,
        db_min=-60.0,
        db_max=12.0,
        db_interval=6.0,
        show_axis_labels=True,
    )

    output = renderer.render(build_render_frame())

    assert "12 dB +" in output
    assert " 6 dB +" in output
    assert "-60 dB +" in output
    assert "-80 dB +" not in output


def test_render_frame_uses_ansi_color_when_enabled() -> None:
    """Rendered output should include ANSI color codes when color is enabled."""
    renderer = TerminalRenderer(color_enabled=True)

    output = renderer.render(build_render_frame())

    assert "\x1b[36m" in output
    assert "\x1b[0m" in output


def test_render_frame_uses_red_for_peak_markers_when_color_enabled() -> None:
    """Peak markers should render in red when color output is enabled."""
    frequencies = tuple(build_log_frequency_centers(20.0, 20_000.0, 32))
    frame = RenderFrame(
        frequencies_hz=frequencies,
        levels_db=tuple([DB_FLOOR] * 32),
        peak_levels_db=tuple([-10.0] * 32),
    )
    renderer = TerminalRenderer(color_enabled=True)

    output = renderer.render(frame)

    assert "\x1b[31m" in output


def test_serialize_bar_row_groups_contiguous_color_runs() -> None:
    """Bar row serialization should reuse one ANSI wrapper per contiguous color run."""
    renderer = TerminalRenderer(color_enabled=True)

    output = renderer._serialize_bar_row(
        ["=", "=", " ", "^", "^"],
        ["\x1b[36m", "\x1b[36m", None, "\x1b[31m", "\x1b[31m"],
    )

    assert output == "\x1b[36m==\x1b[0m \x1b[31m^^\x1b[0m"


def test_render_frame_is_monochrome_when_color_disabled() -> None:
    """Rendered output should not include ANSI color codes in monochrome mode."""
    renderer = TerminalRenderer(color_enabled=False)

    output = renderer.render(build_render_frame())

    assert "\x1b[36m" not in output


def test_render_frame_skips_output_for_identical_second_frame() -> None:
    """A repeated identical frame should not emit redundant terminal output."""
    renderer = TerminalRenderer(color_enabled=False)
    frame = build_render_frame()

    first_output = renderer.render(frame)
    second_output = renderer.render(frame)

    assert not first_output.startswith("\x1b[")
    assert second_output == ""


def test_render_frame_emits_partial_redraw_for_changed_frame() -> None:
    """Changed frames should emit cursor-motion updates instead of a full repaint."""
    renderer = TerminalRenderer(color_enabled=False)
    original = build_render_frame()
    updated = RenderFrame(
        frequencies_hz=original.frequencies_hz,
        levels_db=tuple([DB_FLOOR] + list(original.levels_db[1:])),
        peak_levels_db=original.peak_levels_db,
        history_levels_db=original.history_levels_db,
        freeze_enabled=original.freeze_enabled,
    )

    full_output = renderer.render(original)
    diff_output = renderer.render(updated)

    assert diff_output.startswith("\x1b[")
    assert len(diff_output) < len(full_output)
    assert "\x1b[2K" in diff_output


def test_render_frame_rebuilds_only_changed_bar_rows() -> None:
    """Live redraw should not rebuild every graph row when one band changes."""
    renderer = TerminalRenderer(
        color_enabled=False,
        show_title=False,
        show_shortcuts=False,
    )
    original = build_render_frame()
    updated_levels = list(original.levels_db)
    updated_levels[5] = updated_levels[5] + 12.0
    updated = RenderFrame(
        frequencies_hz=original.frequencies_hz,
        levels_db=tuple(updated_levels),
    )

    renderer.render(original)

    build_calls = 0
    original_build_bar_row = renderer._build_bar_row

    def counting_build_bar_row(*args: object, **kwargs: object) -> str:
        nonlocal build_calls
        build_calls += 1
        return original_build_bar_row(*args, **kwargs)

    renderer._build_bar_row = counting_build_bar_row  # type: ignore[method-assign]

    renderer.render(updated)

    assert 0 < build_calls < len(renderer._row_thresholds)


def test_render_snapshot_omits_reposition_prefix_after_live_render() -> None:
    """Snapshot output should not include redraw control sequences."""
    renderer = TerminalRenderer(color_enabled=False)
    frame = build_render_frame()

    renderer.render(frame)
    snapshot = renderer.render_snapshot(frame, snapshot_format="txt")

    assert not snapshot.startswith("\x1b[")


def test_render_snapshot_txt_strips_ansi_codes() -> None:
    """Plain-text snapshots should strip ANSI color codes."""
    renderer = TerminalRenderer(color_enabled=True)

    snapshot = renderer.render_snapshot(build_render_frame(), snapshot_format="txt")

    assert "\x1b[" not in snapshot


def test_render_snapshot_ansi_preserves_color_codes() -> None:
    """ANSI snapshots should preserve bar colors without redraw prefixes."""
    renderer = TerminalRenderer(color_enabled=True)

    renderer.render(build_render_frame())
    snapshot = renderer.render_snapshot(build_render_frame(), snapshot_format="ansi")

    assert "\x1b[36m" in snapshot
    assert not snapshot.startswith("\x1b[")


def test_render_frame_distributes_frequency_markers_across_axis() -> None:
    """The axis should include aligned label rows across the graph width."""
    renderer = TerminalRenderer(color_enabled=False, show_axis_labels=True)

    output_lines = renderer.render(build_render_frame()).splitlines()

    axis_line = next(line for line in output_lines if line.startswith("        +-"))
    axis_idx = output_lines.index(axis_line)
    label_line_top = output_lines[axis_idx + 1]
    label_line_bottom = output_lines[axis_idx + 2]
    combined_labels = label_line_top + label_line_bottom

    assert axis_line.startswith("        +-")
    assert label_line_top.startswith("         ")
    assert label_line_bottom.startswith("         ")
    assert "20" in combined_labels
    assert "1k" in combined_labels
    assert "20kHz" in combined_labels


def test_render_frame_uses_configured_graph_width() -> None:
    """Bar rows and axis baseline should expand to the configured graph width."""
    renderer = TerminalRenderer(
        color_enabled=False,
        graph_width=120,
        show_axis_labels=True,
    )

    output_lines = renderer.render(build_render_frame()).splitlines()

    zero_db_line = next(line for line in output_lines if line.startswith("   0 dB +"))
    axis_line = next(line for line in output_lines if line.startswith("        +-"))

    assert len(zero_db_line.split("+", maxsplit=1)[1]) == 120
    assert len(axis_line) == len("         ") + 120


def test_render_frame_supports_configurable_graph_height() -> None:
    """Renderer should use the caller-provided row count for graph height."""
    renderer = TerminalRenderer(
        color_enabled=False,
        graph_height=5,
        show_axis_labels=True,
        show_title=False,
        show_shortcuts=False,
    )

    output_lines = renderer.render(build_render_frame()).splitlines()
    axis_line = next(line for line in output_lines if line.startswith("        +-"))

    assert output_lines.index(axis_line) == 5
    assert output_lines[0].startswith("   6 dB +")
    assert output_lines[4].startswith(" -80 dB +")


def test_render_frame_rounds_db_axis_labels_to_whole_numbers() -> None:
    """Displayed dB axis labels should not include decimal places."""
    renderer = TerminalRenderer(
        color_enabled=False,
        db_min=-76.0,
        db_max=0.0,
        graph_height=16,
        show_axis_labels=True,
        show_title=False,
        show_shortcuts=False,
    )

    output = renderer.render(build_render_frame())

    assert "." not in "\n".join(
        line for line in output.splitlines() if " dB +" in line
    )


def test_render_frame_supports_configurable_band_gap() -> None:
    """Configured gaps should propagate vertically through the chart."""
    frequencies = tuple(build_log_frequency_centers(20.0, 20_000.0, 32))
    frame = RenderFrame(
        frequencies_hz=frequencies,
        levels_db=tuple([0.0] * 32),
        peak_levels_db=tuple([0.0] * 32),
    )
    renderer = TerminalRenderer(
        color_enabled=False,
        graph_width=32,
        band_gap=1,
        bar_char="=",
        show_axis_labels=True,
    )

    output_lines = renderer.render(frame).splitlines()
    zero_db_line = next(line for line in output_lines if line.startswith("   0 dB +"))
    axis_line = next(line for line in output_lines if line.startswith("        +-"))
    bar_region = zero_db_line.split("+", maxsplit=1)[1]
    axis_region = axis_line[9:]
    bar_spaces = {
        index for index, character in enumerate(bar_region) if character == " "
    }
    axis_spaces = {
        index for index, character in enumerate(axis_region) if character == " "
    }

    assert len(bar_region) == 32
    assert bar_spaces == axis_spaces
    assert bar_spaces
    assert max(bar_spaces) >= 29
    assert bar_region[0] == "="
    assert len(axis_line) == len("         ") + 32


def test_render_frame_supports_custom_axis_frequencies() -> None:
    """Renderer should use caller-provided axis label frequencies."""
    renderer = TerminalRenderer(
        color_enabled=False,
        show_axis_labels=True,
        axis_frequencies=(50.0, 200.0, 1000.0, 5000.0),
    )

    output = renderer.render(build_render_frame())

    assert "50" in output
    assert "200" in output
    assert "1k" in output
    assert "5kHz" in output
    assert "20kHz" not in output


def test_render_frame_adds_horizontal_axis_notches_for_frequency_labels() -> None:
    """Horizontal axis should place visible notches under labeled frequencies."""
    renderer = TerminalRenderer(
        color_enabled=False,
        graph_width=32,
        show_axis_labels=True,
        axis_frequencies=(20.0, 1000.0, 20000.0),
        show_title=False,
        show_shortcuts=False,
    )

    output_lines = renderer.render(build_render_frame()).splitlines()
    axis_line = next(line for line in output_lines if line.startswith("        +"))

    assert axis_line.count("+") >= 3


def test_render_frame_adds_vertical_axis_notches_for_visible_db_labels() -> None:
    """Visible dB label rows should use a notch at the vertical axis."""
    renderer = TerminalRenderer(
        color_enabled=False,
        show_axis_labels=True,
        db_marker_style="minimal",
        show_title=False,
        show_shortcuts=False,
    )

    output_lines = renderer.render(build_render_frame()).splitlines()
    labeled_rows = [line for line in output_lines if " dB +" in line]

    assert labeled_rows


def test_render_frame_can_overlay_peak_db_labels() -> None:
    """Peak dB labels should render on the row above the associated peak."""
    frame = RenderFrame(
        frequencies_hz=tuple(build_log_frequency_centers(20.0, 20_000.0, 8)),
        levels_db=(-80.0, -80.0, -80.0, -14.0, -80.0, -80.0, -80.0, -80.0),
        peak_levels_db=(-80.0, -80.0, -80.0, -12.0, -80.0, -80.0, -80.0, -80.0),
    )
    renderer = TerminalRenderer(
        color_enabled=False,
        graph_width=48,
        show_title=False,
        show_shortcuts=False,
        peak_char="^",
        peak_db_labels=True,
    )

    output_lines = renderer.render(frame).splitlines()
    label_index = next(
        index for index, line in enumerate(output_lines) if "12" in line
    )
    peak_index = next(index for index, line in enumerate(output_lines) if "^" in line)

    assert label_index < peak_index


def test_render_frame_hides_peak_db_labels_when_band_is_too_narrow() -> None:
    """Peak labels should be omitted when the peak band is narrower than the text."""
    frame = RenderFrame(
        frequencies_hz=tuple(build_log_frequency_centers(20.0, 20_000.0, 16)),
        levels_db=(-80.0,) * 7 + (-14.0,) + (-80.0,) * 8,
        peak_levels_db=(-80.0,) * 7 + (-12.0,) + (-80.0,) * 8,
    )
    renderer = TerminalRenderer(
        color_enabled=False,
        graph_width=16,
        show_title=False,
        show_shortcuts=False,
        peak_char="^",
        peak_db_labels=True,
    )

    output = renderer.render(frame)

    assert "12" not in output


def test_render_frame_hides_peak_db_labels_by_default() -> None:
    """Peak dB value annotations should remain opt-in."""
    frame = RenderFrame(
        frequencies_hz=tuple(build_log_frequency_centers(20.0, 20_000.0, 8)),
        levels_db=(-60.0, -24.0, -60.0, -9.0, -60.0, -18.0, -60.0, -60.0),
        peak_levels_db=(-60.0, -18.0, -60.0, -3.0, -60.0, -12.0, -60.0, -60.0),
    )
    renderer = TerminalRenderer(
        color_enabled=False,
        graph_width=48,
        show_title=False,
        show_shortcuts=False,
    )

    output = renderer.render(frame)

    assert "3" not in output
    assert "12" not in output
    assert "18" not in output


def test_render_frame_supports_configurable_bar_and_peak_characters() -> None:
    """Renderer should honor caller-provided bar and peak characters."""
    frequencies = tuple(build_log_frequency_centers(20.0, 20_000.0, 32))
    levels = tuple([DB_FLOOR] * 32)
    peaks = tuple([-10.0] * 32)
    frame = RenderFrame(
        frequencies_hz=frequencies,
        levels_db=levels,
        peak_levels_db=peaks,
    )
    renderer = TerminalRenderer(
        color_enabled=False,
        db_min=-70.0,
        graph_width=120,
        bar_char="=",
        peak_char="^",
    )

    output = renderer.render(frame)

    assert "^" in output
    assert "=" not in output

    filled_frame = RenderFrame(
        frequencies_hz=frequencies,
        levels_db=tuple([0.0] * 32),
        peak_levels_db=tuple([0.0] * 32),
    )
    filled_output = renderer.render(filled_frame)

    assert "=" in filled_output


def test_auto_color_fallback_disables_color_when_terminal_is_unsupported() -> None:
    """Automatic renderer selection should disable color for unsupported terminals."""
    renderer = TerminalRenderer.auto(is_a_tty=False, term="dumb")

    assert renderer.color_enabled is False
    assert supports_color(is_a_tty=False, term="dumb") is False


def test_supports_color_enables_windows_tty_without_term(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Windows TTY sessions should enable color even if TERM is not set."""
    monkeypatch.setattr(renderer_module.os, "name", "nt")
    monkeypatch.setattr(renderer_module, "_enable_windows_vt_mode", lambda: True)

    assert supports_color(is_a_tty=True, term=None) is True


def test_render_frame_hides_axis_labels_by_default() -> None:
    """Axis labels should be hidden unless explicitly enabled."""
    renderer = TerminalRenderer(color_enabled=False)

    output = renderer.render(build_render_frame())

    assert " dB +" not in output
    assert "1k" not in output
    assert "10k" not in output


def test_render_frame_supports_centered_title_with_version() -> None:
    """Title should render centered to the graph width when enabled."""
    renderer = TerminalRenderer(
        color_enabled=False,
        graph_width=40,
        show_title=True,
        title_text="eq-cli v0.1.0",
    )

    lines = renderer.render(build_render_frame()).splitlines()
    title_line = lines[0]

    assert "eq-cli v0.1.0" in title_line
    assert len(title_line) == len("         ") + 40


def test_render_frame_can_disable_title() -> None:
    """Renderer should omit title line when title output is disabled."""
    with_title = TerminalRenderer(
        color_enabled=False,
        show_title=True,
        title_text="eq-cli v0.1.0",
    )
    without_title = TerminalRenderer(color_enabled=False, show_title=False)

    with_title_lines = with_title.render(build_render_frame()).splitlines()
    without_title_lines = without_title.render(build_render_frame()).splitlines()

    assert len(with_title_lines) == len(without_title_lines) + 1
    assert "eq-cli v0.1.0" in with_title_lines[0]


def test_render_frame_db_marker_style_minimal_reduces_label_count() -> None:
    """Minimal marker style should show fewer visible dB labels."""
    renderer = TerminalRenderer(
        color_enabled=False,
        show_axis_labels=True,
        db_marker_style="minimal",
    )

    output = renderer.render(build_render_frame())
    labeled_rows = [line for line in output.splitlines() if " dB +" in line]

    assert len(labeled_rows) <= 4


def test_render_frame_includes_high_frequency_marker_between_10k_and_20k() -> None:
    """Axis labels should include a marker between 10k and 20k."""
    renderer = TerminalRenderer(color_enabled=False, show_axis_labels=True)

    output = renderer.render(build_render_frame())

    assert "15k" in output


def test_render_frame_allows_terminal_hz_suffix_to_extend_past_graph_width() -> None:
    """The final Hz suffix should be allowed to overflow past the graph edge."""
    renderer = TerminalRenderer(
        color_enabled=False,
        show_axis_labels=True,
        graph_width=32,
    )

    output_lines = renderer.render(build_render_frame()).splitlines()
    axis_line = output_lines[-3]
    label_lines = output_lines[-2:]

    assert any(line.endswith("20kHz") for line in label_lines)
    assert any(len(line) > len(axis_line) for line in label_lines)


def test_render_frame_uses_junction_for_horizontal_axis() -> None:
    """Horizontal axis should join the vertical axis with a visible junction."""
    renderer = TerminalRenderer(color_enabled=False, show_axis_labels=True)

    output_lines = renderer.render(build_render_frame()).splitlines()
    axis_line = next(line for line in output_lines if line.startswith("        +-"))

    assert axis_line.startswith("        +")


def test_render_frame_applies_axis_color_to_vertical_and_horizontal_axes() -> None:
    """Axis color should style both the row separator and the baseline."""
    renderer = TerminalRenderer(
        color_enabled=True,
        show_axis_labels=True,
        axis_color_code="\x1b[33m",
    )

    output = renderer.render(build_render_frame())

    assert "\x1b[33m+\x1b[0m" in output
    assert "\x1b[33m+" in output


def test_render_frame_hides_floor_level_bars_for_silence() -> None:
    """Silence at the floor should not draw a bottom row of bar characters."""
    frequencies = tuple(build_log_frequency_centers(20.0, 20_000.0, 32))
    frame = RenderFrame(
        frequencies_hz=frequencies,
        levels_db=tuple([DB_FLOOR] * 32),
        peak_levels_db=None,
    )
    renderer = TerminalRenderer(color_enabled=False, bar_char="#")

    output = renderer.render(frame)

    assert "#" not in output


def test_render_frame_hides_peak_markers_once_they_reach_floor() -> None:
    """Peak markers should disappear after decaying to the display floor."""
    frequencies = tuple(build_log_frequency_centers(20.0, 20_000.0, 32))
    frame = RenderFrame(
        frequencies_hz=frequencies,
        levels_db=tuple([DB_FLOOR] * 32),
        peak_levels_db=tuple([DB_FLOOR] * 32),
    )
    renderer = TerminalRenderer(color_enabled=False, peak_char="^")

    output = renderer.render(frame)

    assert "^" not in output


def test_render_frame_includes_shortcuts_line_by_default() -> None:
    """Renderer should include the shortcuts legend unless disabled."""
    renderer = TerminalRenderer(color_enabled=False)

    output = renderer.render(build_render_frame())

    assert "[F] Freeze: OFF" in output
    assert "[R] Reset Peaks" in output
    assert "[Q] Quit" in output


def test_render_frame_can_hide_shortcuts_line() -> None:
    """Renderer should omit shortcuts legend when configured off."""
    renderer = TerminalRenderer(color_enabled=False, show_shortcuts=False)

    output = renderer.render(build_render_frame())

    assert "[F] Freeze" not in output


def test_render_frame_shortcuts_line_reflects_freeze_state() -> None:
    """Freeze state in the shortcuts legend should match frame status."""
    frequencies = tuple(build_log_frequency_centers(20.0, 20_000.0, 32))
    frame = RenderFrame(
        frequencies_hz=frequencies,
        levels_db=tuple([DB_FLOOR] * 32),
        freeze_enabled=True,
    )
    renderer = TerminalRenderer(color_enabled=False)

    output = renderer.render(frame)

    assert "[F] Freeze: ON" in output


def test_render_frame_can_render_history_rows() -> None:
    """Renderer should append configured history rows beneath the main plot."""
    frame = build_render_frame()
    history_row = tuple([0.0] * len(frame.levels_db))
    with_history = RenderFrame(
        frequencies_hz=frame.frequencies_hz,
        levels_db=frame.levels_db,
        history_levels_db=(history_row, history_row),
    )
    renderer = TerminalRenderer(
        color_enabled=False,
        show_shortcuts=False,
        history_rows=2,
    )

    output_lines = renderer.render(with_history).splitlines()
    history_lines = [line for line in output_lines if line.startswith("        |")]

    assert len(history_lines) >= 2


def test_render_frame_limits_history_rows_to_configured_count() -> None:
    """Renderer should cap displayed history rows to the configured max."""
    frame = build_render_frame()
    history_row = tuple([0.0] * len(frame.levels_db))
    with_history = RenderFrame(
        frequencies_hz=frame.frequencies_hz,
        levels_db=frame.levels_db,
        history_levels_db=(history_row, history_row, history_row),
    )
    no_history_renderer = TerminalRenderer(color_enabled=False, show_shortcuts=False)
    limited_renderer = TerminalRenderer(
        color_enabled=False,
        show_shortcuts=False,
        history_rows=1,
    )

    no_history_count = len(no_history_renderer.render(frame).splitlines())
    limited_count = len(limited_renderer.render(with_history).splitlines())

    assert limited_count == no_history_count + 1


def test_render_frame_history_rows_use_custom_gradient() -> None:
    """History rows should map levels using the configured gradient."""
    frame = build_render_frame()
    history_low = tuple([DB_FLOOR] * len(frame.levels_db))
    history_high = tuple([6.0] * len(frame.levels_db))
    with_history = RenderFrame(
        frequencies_hz=frame.frequencies_hz,
        levels_db=frame.levels_db,
        history_levels_db=(history_low, history_high),
    )
    renderer = TerminalRenderer(
        color_enabled=False,
        show_shortcuts=False,
        history_rows=2,
        history_gradient=".#",
    )

    output = renderer.render(with_history)

    assert "." in output
    assert "#" in output


def test_render_frame_rejects_empty_history_gradient() -> None:
    """Renderer should reject empty history gradient strings."""
    with pytest.raises(ValueError, match="History gradient must not be empty"):
        TerminalRenderer(color_enabled=False, history_gradient="")


def test_render_frame_history_rows_use_history_color_override() -> None:
    """History rows should use dedicated history color when configured."""
    frame = build_render_frame()
    history_row = tuple([0.0] * len(frame.levels_db))
    with_history = RenderFrame(
        frequencies_hz=frame.frequencies_hz,
        levels_db=frame.levels_db,
        history_levels_db=(history_row,),
    )
    renderer = TerminalRenderer(
        color_enabled=True,
        show_shortcuts=False,
        history_rows=1,
        history_color_code="\x1b[33m",
    )

    output = renderer.render(with_history)

    assert "\x1b[33m" in output


# ---------------------------------------------------------------------------
# m1: 'spaced' vs 'all' db marker style
# ---------------------------------------------------------------------------


def test_render_frame_db_marker_style_spaced_shows_only_interval_rows() -> None:
    """'spaced' must label only interval-aligned rows, not every row."""
    renderer_spaced = TerminalRenderer(
        color_enabled=False,
        show_axis_labels=True,
        db_marker_style="spaced",
        db_min=-60.0,
        db_max=0.0,
        db_interval=10.0,
    )
    renderer_all = TerminalRenderer(
        color_enabled=False,
        show_axis_labels=True,
        db_marker_style="all",
        db_min=-60.0,
        db_max=0.0,
        db_interval=10.0,
    )

    frame = build_render_frame()
    output_spaced = renderer_spaced.render(frame)
    output_all = renderer_all.render(frame)

    labeled_spaced = [line for line in output_spaced.splitlines() if " dB +" in line]
    labeled_all = [line for line in output_all.splitlines() if " dB +" in line]

    # 'spaced' must show fewer (or equal) labels than 'all'.
    assert len(labeled_spaced) <= len(labeled_all)
    # 'spaced' must show at least 2 labeled rows (0 dB and -60 dB).
    assert len(labeled_spaced) >= 2
    # 'all' must label every bar row.
    bar_row_count = sum(
        1
        for line in output_all.splitlines()
        if "+" in line and " dB " in line
    )
    assert len(labeled_all) == bar_row_count


def test_render_frame_db_marker_style_all_labels_every_row() -> None:
    """'all' must add a dB label on every bar row when axis_labels is enabled."""
    renderer = TerminalRenderer(
        color_enabled=False,
        show_axis_labels=True,
        db_marker_style="all",
        db_min=-20.0,
        db_max=0.0,
        db_interval=10.0,
        graph_height=5,
    )

    frame = build_render_frame()
    output = renderer.render(frame)

    labeled_rows = [line for line in output.splitlines() if " dB +" in line]
    assert len(labeled_rows) == 5


# ---------------------------------------------------------------------------
# m3: bisect-based _find_peak_row
# ---------------------------------------------------------------------------


def test_find_peak_row_returns_row_at_or_above_peak() -> None:
    """_find_peak_row must return the threshold at or just above the peak level."""
    renderer = TerminalRenderer(
        color_enabled=False,
        db_min=-80.0,
        db_max=0.0,
        db_interval=10.0,
    )

    # Peak exactly on a threshold — should return that threshold.
    row_at = renderer._find_peak_row(-10.0)
    assert row_at == pytest.approx(-10.0, abs=0.1)

    # Peak between two thresholds — result must be above the peak.
    row_above = renderer._find_peak_row(-5.5)
    assert row_above >= -5.5


def test_find_peak_row_index_and_find_peak_row_are_consistent() -> None:
    """_find_peak_row_index must return the index of _find_peak_row's threshold."""
    renderer = TerminalRenderer(
        color_enabled=False,
        db_min=-80.0,
        db_max=0.0,
        db_interval=10.0,
    )

    for peak_db in (-70.0, -40.0, -10.0, 0.0):
        threshold = renderer._find_peak_row(peak_db)
        index = renderer._find_peak_row_index(peak_db)
        assert renderer._row_thresholds[index] == pytest.approx(threshold, abs=0.01)


# ---------------------------------------------------------------------------
# m10: bounded caches
# ---------------------------------------------------------------------------


def test_spectrum_processor_frame_cache_bounded() -> None:
    """SpectrumProcessor._frame_size_cache must not exceed _FRAME_CACHE_MAX_SIZE."""
    processor = SpectrumProcessor(sample_rate=44100, band_count=32)

    for size in range(128, 128 + _FRAME_CACHE_MAX_SIZE + 4):
        frame = AudioFrame(
            samples=np.zeros(size, dtype=np.float64),
            sample_rate=44100,
        )
        try:
            processor.process_frame(frame)
        except Exception:
            pass

    assert len(processor._frame_size_cache) <= _FRAME_CACHE_MAX_SIZE


def test_renderer_layout_cache_bounded() -> None:
    """TerminalRenderer._layout_cache must not exceed _LAYOUT_CACHE_MAX_SIZE."""
    renderer = TerminalRenderer(color_enabled=False)

    for band_count in range(8, 8 + _LAYOUT_CACHE_MAX_SIZE + 4):
        freqs = tuple(build_log_frequency_centers(20.0, 20_000.0, band_count))
        levels = tuple(0.0 for _ in freqs)
        frame = RenderFrame(frequencies_hz=freqs, levels_db=levels)
        renderer.render(frame)

    assert len(renderer._layout_cache) <= _LAYOUT_CACHE_MAX_SIZE
