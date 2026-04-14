from __future__ import annotations

import bisect
import math
import os
import re
from collections import OrderedDict
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal, Protocol, cast

RESET = "\x1b[0m"
CYAN = "\x1b[36m"
RED = "\x1b[31m"
AXIS_SEPARATOR = "|"
AXIS_JUNCTION = "+"
_LAYOUT_CACHE_MAX_SIZE = 8

DB_MIN_DEFAULT = -80.0
DB_MAX_DEFAULT = 6.0
DB_INTERVAL_DEFAULT = 10.0
GRAPH_HEIGHT_DEFAULT = 0
GRAPH_WIDTH_DEFAULT = 120
BAND_GAP_DEFAULT = 0
BAR_CHAR_DEFAULT = "#"
PEAK_CHAR_DEFAULT = "-"
DB_MARKER_STYLE_DEFAULT = "spaced"
_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")


class _Kernel32Api(Protocol):
    """Subset of the Windows console API used for ANSI mode setup."""

    def GetStdHandle(self, handle_id: int) -> int:
        """Return the OS handle for the requested standard stream."""

    def GetConsoleMode(self, handle: int, mode: object) -> int:
        """Load the current console mode into the provided pointer."""

    def SetConsoleMode(self, handle: int, mode: int) -> int:
        """Apply a new console mode for the provided handle."""


class _WindowsDllLoader(Protocol):
    """ctypes loader wrapper exposing the kernel32 console functions."""

    kernel32: _Kernel32Api


@dataclass(frozen=True)
class RenderFrame:
    """A renderable snapshot of log-spaced spectrum levels."""

    frequencies_hz: tuple[float, ...]
    levels_db: tuple[float, ...]
    peak_levels_db: tuple[float, ...] | None = None
    history_levels_db: tuple[tuple[float, ...], ...] | None = None
    freeze_enabled: bool = False


@dataclass(frozen=True)
class _RenderLayout:
    """Cached static layout data derived from the frame frequencies."""

    separator_columns: frozenset[int]
    axis_notch_columns: frozenset[int]
    band_columns: tuple[tuple[int, ...], ...]
    band_spans: tuple[tuple[tuple[int, int], ...], ...]
    frequency_axis_lines: tuple[str, ...]


HISTORY_GRADIENT = " .:-=+*#%@"


class TerminalRenderer:
    """Render spectrum frames into a terminal-friendly text representation."""

    _AXIS_MARKERS_HZ = (
        20.0,
        50.0,
        100.0,
        200.0,
        500.0,
        1_000.0,
        2_000.0,
        5_000.0,
        10_000.0,
        15_000.0,
        20_000.0,
    )

    @classmethod
    def auto(
        cls,
        is_a_tty: bool,
        term: str | None,
        db_min: float = DB_MIN_DEFAULT,
        db_max: float = DB_MAX_DEFAULT,
        db_interval: float = DB_INTERVAL_DEFAULT,
        graph_height: int = GRAPH_HEIGHT_DEFAULT,
        graph_width: int = GRAPH_WIDTH_DEFAULT,
        band_gap: int = BAND_GAP_DEFAULT,
        axis_frequencies: Sequence[float] | None = None,
        bar_char: str = BAR_CHAR_DEFAULT,
        peak_char: str = PEAK_CHAR_DEFAULT,
        peak_db_labels: bool = False,
        history_rows: int = 0,
        history_gradient: str = HISTORY_GRADIENT,
        show_shortcuts: bool = True,
        show_axis_labels: bool = False,
        show_title: bool = True,
        title_text: str | None = None,
        db_marker_style: str = DB_MARKER_STYLE_DEFAULT,
        bar_color_code: str = CYAN,
        peak_color_code: str = RED,
        history_color_code: str | None = None,
        axis_color_code: str | None = None,
        label_color_code: str | None = None,
    ) -> TerminalRenderer:
        """Create a renderer that enables color only when the terminal supports it."""
        return cls(
            color_enabled=supports_color(is_a_tty=is_a_tty, term=term),
            db_min=db_min,
            db_max=db_max,
            db_interval=db_interval,
            graph_height=graph_height,
            graph_width=graph_width,
            band_gap=band_gap,
            axis_frequencies=axis_frequencies,
            bar_char=bar_char,
            peak_char=peak_char,
            peak_db_labels=peak_db_labels,
            history_rows=history_rows,
            history_gradient=history_gradient,
            show_shortcuts=show_shortcuts,
            show_axis_labels=show_axis_labels,
            show_title=show_title,
            title_text=title_text,
            db_marker_style=db_marker_style,
            bar_color_code=bar_color_code,
            peak_color_code=peak_color_code,
            history_color_code=history_color_code,
            axis_color_code=axis_color_code,
            label_color_code=label_color_code,
        )

    def __init__(
        self,
        color_enabled: bool,
        db_min: float = DB_MIN_DEFAULT,
        db_max: float = DB_MAX_DEFAULT,
        db_interval: float = DB_INTERVAL_DEFAULT,
        graph_height: int = GRAPH_HEIGHT_DEFAULT,
        graph_width: int = GRAPH_WIDTH_DEFAULT,
        band_gap: int = BAND_GAP_DEFAULT,
        axis_frequencies: Sequence[float] | None = None,
        bar_char: str = BAR_CHAR_DEFAULT,
        peak_char: str = PEAK_CHAR_DEFAULT,
        peak_db_labels: bool = False,
        history_rows: int = 0,
        history_gradient: str = HISTORY_GRADIENT,
        show_shortcuts: bool = True,
        show_axis_labels: bool = False,
        show_title: bool = True,
        title_text: str | None = None,
        db_marker_style: str = DB_MARKER_STYLE_DEFAULT,
        bar_color_code: str = CYAN,
        peak_color_code: str = RED,
        history_color_code: str | None = None,
        axis_color_code: str | None = None,
        label_color_code: str | None = None,
    ) -> None:
        """Create a renderer with optional ANSI color output."""
        if graph_height <= 0:
            graph_height = _default_graph_height(db_min, db_max, db_interval)
        if graph_width <= 0:
            raise ValueError("Graph width must be greater than zero.")
        if band_gap < 0:
            raise ValueError("Band gap must be zero or greater.")
        if len(bar_char) != 1:
            raise ValueError("Bar character must be exactly one character.")
        if len(peak_char) != 1:
            raise ValueError("Peak character must be exactly one character.")
        if history_rows < 0:
            raise ValueError("History rows must be zero or greater.")
        if not history_gradient:
            raise ValueError("History gradient must not be empty.")
        if db_marker_style not in {"all", "spaced", "minimal"}:
            raise ValueError("dB marker style must be all, spaced, or minimal.")
        self.color_enabled = color_enabled
        self._db_min = db_min
        self._db_max = db_max
        self._graph_width = graph_width
        self._band_gap = band_gap
        self._axis_frequencies = tuple(axis_frequencies) if axis_frequencies else None
        self._bar_char = bar_char
        self._peak_char = peak_char
        self._peak_db_labels = peak_db_labels
        self._history_rows = history_rows
        self._history_gradient = history_gradient
        self._show_shortcuts = show_shortcuts
        self._show_axis_labels = show_axis_labels
        self._show_title = show_title
        self._title_text = title_text or "eq-cli"
        self._db_marker_style = db_marker_style
        self._bar_color_code = bar_color_code
        self._peak_color_code = peak_color_code
        self._history_color_code = history_color_code or bar_color_code
        self._axis_color_code = axis_color_code
        self._label_color_code = label_color_code
        self._row_thresholds = _build_row_thresholds(
            db_min=db_min,
            db_max=db_max,
            graph_height=graph_height,
        )
        # For "all" style every row gets a label; other styles use interval markers.
        if db_marker_style == "all":
            self._db_marker_labels = {
                index: str(int(round(threshold)))
                for index, threshold in enumerate(self._row_thresholds)
            }
        else:
            self._db_marker_labels = _build_db_marker_labels(
                row_thresholds=self._row_thresholds,
                db_min=db_min,
                db_max=db_max,
                db_interval=db_interval,
            )
        self._marker_rows = tuple(sorted(self._db_marker_labels))
        # Ascending copy of row_thresholds used for O(log n) bisect lookups.
        self._row_thresholds_asc: list[float] = list(reversed(self._row_thresholds))
        self._lines_rendered: int = 0
        self._previous_lines: tuple[str, ...] | None = None
        self._previous_frame: RenderFrame | None = None
        self._layout_cache: OrderedDict[
            tuple[tuple[float, ...], int], _RenderLayout
        ] = OrderedDict()

    def render(self, frame: RenderFrame) -> str:
        """Render a frame with dB rows, bars, and a frequency axis."""
        return self._render_chart(frame, include_reposition=True)

    def render_snapshot(
        self,
        frame: RenderFrame,
        snapshot_format: Literal["txt", "ansi"] = "txt",
    ) -> str:
        """Render a frame for saving to disk without redraw control sequences."""
        output = self._render_chart(frame, include_reposition=False)
        if snapshot_format == "txt":
            return _ANSI_ESCAPE_RE.sub("", output)
        return output

    def _render_chart(self, frame: RenderFrame, include_reposition: bool) -> str:
        """Render a frame, optionally adding in-place redraw control sequences."""
        if (
            include_reposition
            and self._previous_frame == frame
            and self._previous_lines is not None
        ):
            return ""

        peak_markers = self._compute_peak_markers(frame)
        axis_prefix = self._axis_prefix()
        total_graph_width = self._graph_width
        layout = self._layout_for_frame(frame, axis_prefix)
        separator_columns = layout.separator_columns
        band_columns = list(layout.band_columns)
        band_spans = layout.band_spans
        peak_label_overlays = self._compute_peak_label_overlays(frame, band_columns)
        if include_reposition and self._can_reuse_live_lines(frame):
            lines = self._reuse_live_lines(
                frame=frame,
                peak_markers=peak_markers,
                peak_label_overlays=peak_label_overlays,
                band_spans=band_spans,
                axis_prefix=axis_prefix,
                total_graph_width=total_graph_width,
            )
        else:
            lines = self._build_full_lines(
                frame=frame,
                layout=layout,
                peak_markers=peak_markers,
                peak_label_overlays=peak_label_overlays,
                band_spans=band_spans,
                axis_prefix=axis_prefix,
                total_graph_width=total_graph_width,
                separator_columns=separator_columns,
            )
        output = "\n".join(lines) + "\n"
        if not include_reposition:
            return output

        rendered = self._render_live_lines(lines)
        self._previous_lines = tuple(lines)
        self._previous_frame = frame
        self._lines_rendered = len(lines)
        return rendered

    def _build_full_lines(
        self,
        frame: RenderFrame,
        layout: _RenderLayout,
        peak_markers: set[tuple[int, float]],
        peak_label_overlays: dict[int, list[tuple[int, str]]],
        band_spans: tuple[tuple[tuple[int, int], ...], ...],
        axis_prefix: str,
        total_graph_width: int,
        separator_columns: frozenset[int],
    ) -> list[str]:
        """Build all logical lines for a frame from scratch."""
        lines: list[str] = []
        if self._show_title:
            centered_title = self._title_text.center(total_graph_width)
            lines.append(
                axis_prefix
                + self._colorize(centered_title, self._label_color_code)
            )

        for row_index, threshold in enumerate(self._row_thresholds):
            lines.append(
                self._build_graph_line(
                    frame=frame,
                    threshold=threshold,
                    row_index=row_index,
                    peak_markers=peak_markers,
                    peak_label_overlays=peak_label_overlays,
                    band_spans=band_spans,
                    total_graph_width=total_graph_width,
                )
            )

        lines.append(
            self._build_axis_line(
                layout,
                total_graph_width,
                separator_columns,
            )
        )
        if self._show_axis_labels:
            lines.extend(layout.frequency_axis_lines)
        lines.extend(
            self._build_history_lines(
                frame=frame,
                band_spans=band_spans,
                total_graph_width=total_graph_width,
            )
        )
        if self._show_shortcuts:
            lines.append(self._build_shortcuts_line(axis_prefix, frame.freeze_enabled))
        return lines

    def _can_reuse_live_lines(self, frame: RenderFrame) -> bool:
        """Return whether the previous logical lines can be reused for this frame."""
        if self._previous_lines is None or self._previous_frame is None:
            return False
        if self._previous_frame.frequencies_hz != frame.frequencies_hz:
            return False
        if len(self._previous_frame.levels_db) != len(frame.levels_db):
            return False
        return len(self._previous_lines) == self._expected_line_count(frame)

    def _expected_line_count(self, frame: RenderFrame) -> int:
        """Return the total rendered line count for the provided frame."""
        history_count = min(self._history_rows, len(frame.history_levels_db or ()))
        return (
            (1 if self._show_title else 0)
            + len(self._row_thresholds)
            + 1
            + (2 if self._show_axis_labels else 0)
            + history_count
            + (1 if self._show_shortcuts else 0)
        )

    def _reuse_live_lines(
        self,
        frame: RenderFrame,
        peak_markers: set[tuple[int, float]],
        peak_label_overlays: dict[int, list[tuple[int, str]]],
        band_spans: tuple[tuple[tuple[int, int], ...], ...],
        axis_prefix: str,
        total_graph_width: int,
    ) -> list[str]:
        """Reuse previous logical lines and rebuild only dynamic rows that changed."""
        previous_frame = cast(RenderFrame, self._previous_frame)
        lines = list(cast(tuple[str, ...], self._previous_lines))
        graph_start = 1 if self._show_title else 0

        for row_index in self._changed_graph_row_indices(previous_frame, frame):
            lines[graph_start + row_index] = self._build_graph_line(
                frame=frame,
                threshold=self._row_thresholds[row_index],
                row_index=row_index,
                peak_markers=peak_markers,
                peak_label_overlays=peak_label_overlays,
                band_spans=band_spans,
                total_graph_width=total_graph_width,
            )

        history_start = graph_start + len(self._row_thresholds) + 1
        if self._show_axis_labels:
            history_start += 2

        previous_history = (previous_frame.history_levels_db or ())[
            -self._history_rows :
        ]
        current_history = (frame.history_levels_db or ())[-self._history_rows :]
        for history_index, (previous_row, current_row) in enumerate(
            zip(previous_history, current_history, strict=False)
        ):
            if previous_row == current_row:
                continue
            lines[history_start + history_index] = self._build_history_line(
                current_row,
                band_spans,
                total_graph_width,
            )

        if (
            self._show_shortcuts
            and frame.freeze_enabled != previous_frame.freeze_enabled
        ):
            lines[-1] = self._build_shortcuts_line(axis_prefix, frame.freeze_enabled)

        return lines

    def _changed_graph_row_indices(
        self,
        previous_frame: RenderFrame,
        frame: RenderFrame,
    ) -> set[int]:
        """Return graph row indexes whose rendered bar content changed."""
        if previous_frame.peak_levels_db != frame.peak_levels_db:
            return set(range(len(self._row_thresholds)))

        changed_rows: set[int] = set()
        for previous_level, current_level in zip(
            previous_frame.levels_db,
            frame.levels_db,
            strict=False,
        ):
            if previous_level == current_level:
                continue
            for row_index, threshold in enumerate(self._row_thresholds):
                if self._fills_bar(previous_level, threshold) != self._fills_bar(
                    current_level,
                    threshold,
                ):
                    changed_rows.add(row_index)
        return changed_rows

    def _build_graph_line(
        self,
        frame: RenderFrame,
        threshold: float,
        row_index: int,
        peak_markers: set[tuple[int, float]],
        peak_label_overlays: dict[int, list[tuple[int, str]]],
        band_spans: tuple[tuple[tuple[int, int], ...], ...],
        total_graph_width: int,
    ) -> str:
        """Build one full graph line including the left-side prefix."""
        bars = self._build_bar_row(
            levels_db=frame.levels_db,
            threshold_db=threshold,
            row_index=row_index,
            peak_markers=peak_markers,
            peak_label_overlays=peak_label_overlays,
            band_spans=band_spans,
            total_width=total_graph_width,
        )
        prefix = self._format_row_prefix(
            self._db_marker_labels.get(row_index),
            row_index,
        )
        return prefix + bars

    def _build_axis_line(
        self,
        layout: _RenderLayout,
        total_graph_width: int,
        separator_columns: frozenset[int],
    ) -> str:
        """Build the horizontal axis line."""
        baseline = list("-" * total_graph_width)
        self._apply_separators(baseline, separator_columns)
        self._apply_axis_notches(
            baseline,
            set(layout.axis_notch_columns),
        )
        return (
            self._axis_padding()
            + self._colorize(AXIS_JUNCTION, self._axis_color_code)
            + self._colorize("".join(baseline), self._axis_color_code)
        )

    def _build_shortcuts_line(self, axis_prefix: str, freeze_enabled: bool) -> str:
        """Build the shortcuts/status line."""
        return axis_prefix + self._colorize(
            self._shortcuts_line(freeze_enabled),
            self._label_color_code,
        )

    def _fills_bar(self, level_db: float, threshold_db: float) -> bool:
        """Return whether a band level fills the current dB row."""
        if level_db <= self._db_min:
            return False
        return level_db >= max(self._db_min, threshold_db)

    def _layout_for_frame(
        self,
        frame: RenderFrame,
        axis_prefix: str,
    ) -> _RenderLayout:
        """Return cached static layout data for a frame's frequency geometry."""
        key = (frame.frequencies_hz, len(frame.levels_db))
        layout = self._layout_cache.get(key)
        if layout is not None:
            return layout

        separator_columns = frozenset(self._separator_columns(frame.frequencies_hz))
        axis_notch_columns = frozenset(self._axis_notch_columns(frame.frequencies_hz))
        band_columns = tuple(
            self._build_band_columns(
                len(frame.levels_db),
                set(separator_columns),
            )
        )
        band_spans = tuple(self._build_band_spans(band_columns))
        frequency_axis_lines = tuple(
            self._build_frequency_axis_lines(
                frame.frequencies_hz,
                axis_prefix,
                self._graph_width,
            )
        )
        layout = _RenderLayout(
            separator_columns=separator_columns,
            axis_notch_columns=axis_notch_columns,
            band_columns=band_columns,
            band_spans=band_spans,
            frequency_axis_lines=frequency_axis_lines,
        )
        if len(self._layout_cache) >= _LAYOUT_CACHE_MAX_SIZE:
            self._layout_cache.popitem(last=False)
        self._layout_cache[key] = layout
        return layout

    def _render_live_lines(self, lines: list[str]) -> str:
        """Return terminal output that updates only changed lines when possible."""
        output = "\n".join(lines) + "\n"
        if self._lines_rendered == 0 or self._previous_lines is None:
            return output
        if len(lines) != self._lines_rendered:
            return f"\x1b[{self._lines_rendered}A" + output

        changed_rows = [
            index
            for index, (previous, current) in enumerate(
                zip(self._previous_lines, lines, strict=False)
            )
            if previous != current
        ]
        if not changed_rows:
            return ""

        fragments: list[str] = []
        current_row = self._lines_rendered
        for row_index in sorted(changed_rows, reverse=True):
            rows_up = current_row - row_index
            if rows_up > 0:
                fragments.append(f"\x1b[{rows_up}A")
            fragments.append("\r\x1b[2K")
            fragments.append(lines[row_index])
            current_row = row_index

        fragments.append("\r")
        rows_down = self._lines_rendered - current_row
        if rows_down > 0:
            fragments.append(f"\x1b[{rows_down}B")
        fragments.append("\r")
        return "".join(fragments)

    def _build_history_lines(
        self,
        frame: RenderFrame,
        band_spans: tuple[tuple[tuple[int, int], ...], ...],
        total_graph_width: int,
    ) -> list[str]:
        """Render history rows as a lightweight waterfall under the axis."""
        if self._history_rows <= 0 or frame.history_levels_db is None:
            return []

        visible_history = frame.history_levels_db[-self._history_rows :]
        history_lines: list[str] = []
        for history_row in visible_history:
            history_lines.append(
                self._build_history_line(
                    history_row,
                    band_spans,
                    total_graph_width,
                )
            )

        return history_lines

    def _build_history_line(
        self,
        history_row: tuple[float, ...],
        band_spans: tuple[tuple[tuple[int, int], ...], ...],
        total_graph_width: int,
    ) -> str:
        """Render one history line from a single history row."""
        row = [" "] * total_graph_width
        for level_db, spans in zip(history_row, band_spans, strict=False):
            character = self._history_char(level_db)
            if character == " ":
                continue
            for start, end in spans:
                row[start:end] = character * (end - start)
        return (
            self._axis_padding()
            + self._colorize(AXIS_SEPARATOR, self._axis_color_code)
            + self._colorize("".join(row), self._history_color_code)
        )

    def _history_char(self, level_db: float) -> str:
        """Map a dB level to a gradient character for history rendering."""
        db_span = self._db_max - self._db_min
        if db_span <= 0:
            return self._history_gradient[0]
        normalized = max(0.0, min(1.0, (level_db - self._db_min) / db_span))
        index = int(normalized * (len(self._history_gradient) - 1))
        return self._history_gradient[index]

    @staticmethod
    def _shortcuts_line(freeze_enabled: bool) -> str:
        """Return the runtime keyboard shortcuts/status legend."""
        freeze_text = "ON" if freeze_enabled else "OFF"
        return (
            f"[F] Freeze: {freeze_text}  [R] Reset Peaks  [S] Snapshot  "
            "[P] Export Profile  [Q] Quit"
        )

    def _format_row_prefix(
        self,
        label: str | None,
        row_index: int,
    ) -> str:
        """Return the dB label/prefix for one rendered row."""
        marker_width = self._axis_label_width()
        if not self._show_axis_labels:
            return (
                f"{' ' * marker_width}"
                f"{self._colorize(AXIS_SEPARATOR, self._axis_color_code)}"
            )
        if label is None or not self._show_db_marker(row_index):
            return (
                f"{' ' * marker_width}"
                f"{self._colorize(AXIS_SEPARATOR, self._axis_color_code)}"
            )

        marker = f"{label:>4} dB "
        return (
            self._colorize(marker, self._label_color_code)
            + self._colorize(AXIS_JUNCTION, self._axis_color_code)
        )

    def _show_db_marker(self, row_index: int) -> bool:
        """Return whether to show the row dB marker for the selected style."""
        if self._db_marker_style == "all":
            return True
        if self._db_marker_style == "spaced":
            return row_index in self._db_marker_labels
        # minimal: first, last, and midpoint of the marker rows only.
        if not self._marker_rows:
            return False
        if row_index == self._marker_rows[0] or row_index == self._marker_rows[-1]:
            return True
        midpoint = len(self._marker_rows) // 2
        return row_index == self._marker_rows[midpoint]

    def _build_bar_row(
        self,
        levels_db: tuple[float, ...],
        threshold_db: float,
        row_index: int,
        peak_markers: set[tuple[int, float]],
        peak_label_overlays: dict[int, list[tuple[int, str]]],
        band_spans: tuple[tuple[tuple[int, int], ...], ...],
        total_width: int,
    ) -> str:
        """Build a single rendered dB row including any configured inter-band gaps."""
        row = [" "] * total_width
        color_codes: list[str | None] = [None] * total_width
        for index, (level_db, spans) in enumerate(
            zip(levels_db, band_spans, strict=False)
        ):
            fill_char, color_code = self._render_bar_fill(
                level_db=level_db,
                threshold_db=threshold_db,
                is_peak_row=(index, threshold_db) in peak_markers,
            )
            if fill_char is None:
                continue
            for start, end in spans:
                span_width = end - start
                row[start:end] = fill_char * span_width
                if color_code is not None:
                    color_codes[start:end] = [color_code] * span_width
        for start, label in peak_label_overlays.get(row_index, []):
            for offset, character in enumerate(label):
                column = start + offset
                if 0 <= column < len(row):
                    row[column] = character
                    if self.color_enabled:
                        color_codes[column] = self._peak_color_code
        return self._serialize_bar_row(row, color_codes)

    def _compute_peak_markers(
        self, frame: RenderFrame
    ) -> set[tuple[int, float]]:
        """Return (band_index, threshold) pairs that should display a peak marker."""
        if frame.peak_levels_db is None:
            return set()
        return {
            (index, self._find_peak_row(peak_db))
            for index, peak_db in enumerate(frame.peak_levels_db)
            if peak_db > self._db_min
        }

    def _compute_peak_label_overlays(
        self,
        frame: RenderFrame,
        band_columns: list[tuple[int, ...]],
    ) -> dict[int, list[tuple[int, str]]]:
        """Return non-overlapping peak dB labels positioned above peaks."""
        if not self._peak_db_labels or frame.peak_levels_db is None:
            return {}

        candidates = self._peak_label_candidates(frame, band_columns)
        overlays: dict[int, list[tuple[int, str]]] = {}
        used_ranges: dict[int, list[tuple[int, int]]] = {}
        for row_index, start, end, label in candidates:
            row_ranges = used_ranges.setdefault(row_index, [])
            overlaps = any(
                not (end <= used_start or start >= used_end)
                for used_start, used_end in row_ranges
            )
            if overlaps:
                continue
            overlays.setdefault(row_index, []).append((start, label))
            row_ranges.append((start, end))
        return overlays

    def _peak_label_candidates(
        self,
        frame: RenderFrame,
        band_columns: list[tuple[int, ...]],
    ) -> list[tuple[int, int, int, str]]:
        """Return label placements for local peak maxima with room above them."""
        if frame.peak_levels_db is None:
            return []

        candidates: list[tuple[int, int, int, str]] = []
        for index, peak_db in enumerate(frame.peak_levels_db):
            if peak_db <= self._db_min:
                continue
            columns = band_columns[index] if index < len(band_columns) else ()
            if not columns:
                continue
            left = frame.peak_levels_db[index - 1] if index > 0 else self._db_min
            right = (
                frame.peak_levels_db[index + 1]
                if index + 1 < len(frame.peak_levels_db)
                else self._db_min
            )
            if peak_db < left or peak_db < right:
                continue
            candidate = self._make_peak_label_candidate(peak_db, columns)
            if candidate is None:
                continue
            candidates.append(candidate)

        candidates.sort()
        return candidates

    def _make_peak_label_candidate(
        self,
        peak_db: float,
        columns: tuple[int, ...],
    ) -> tuple[int, int, int, str] | None:
        """Build one candidate label placement above a peak if it fits."""
        if not columns:
            return None

        label = str(abs(int(round(peak_db))))
        if len(label) > len(columns):
            return None

        row_index = self._find_peak_row_index(peak_db) - 1
        if row_index < 0:
            return None

        start = columns[0] + ((len(columns) - len(label)) // 2)
        end = start + len(label)
        if start < columns[0] or end > columns[-1] + 1:
            return None
        return (row_index, start, end, label)

    def _find_peak_row(self, peak_db: float) -> float:
        """Return the smallest row threshold at or above the peak level."""
        asc = self._row_thresholds_asc
        index = bisect.bisect_left(asc, peak_db)
        if index >= len(asc):
            index = len(asc) - 1
        return asc[index]

    def _find_peak_row_index(self, peak_db: float) -> int:
        """Return the rendered row index used for a peak marker."""
        asc = self._row_thresholds_asc
        index = bisect.bisect_left(asc, peak_db)
        if index >= len(asc):
            index = len(asc) - 1
        # Row index in the original descending list is the mirror position.
        return len(self._row_thresholds) - 1 - index

    def _render_bar_fill(
        self,
        level_db: float,
        threshold_db: float,
        is_peak_row: bool = False,
    ) -> tuple[str | None, str | None]:
        if is_peak_row and level_db < threshold_db:
            return (
                self._peak_char,
                self._peak_color_code if self.color_enabled else None,
            )
        if level_db <= self._db_min:
            return None, None
        if level_db < max(self._db_min, threshold_db):
            return None, None
        return (
            self._bar_char,
            self._bar_color_code if self.color_enabled else None,
        )

    @staticmethod
    def _build_band_spans(
        band_columns: tuple[tuple[int, ...], ...],
    ) -> list[tuple[tuple[int, int], ...]]:
        """Collapse each band's columns into contiguous half-open spans."""
        band_spans: list[tuple[tuple[int, int], ...]] = []
        for columns in band_columns:
            if not columns:
                band_spans.append(())
                continue

            spans: list[tuple[int, int]] = []
            start = columns[0]
            previous = columns[0]
            for column in columns[1:]:
                if column == previous + 1:
                    previous = column
                    continue
                spans.append((start, previous + 1))
                start = column
                previous = column
            spans.append((start, previous + 1))
            band_spans.append(tuple(spans))
        return band_spans

    def _build_frequency_axis(self, frequencies_hz: tuple[float, ...]) -> str:
        if not frequencies_hz:
            return "     0 Hz"

        return (
            "     "
            f"{self._format_frequency(frequencies_hz[0])}"
            " ... "
            f"{self._format_frequency(frequencies_hz[-1])}"
        )

    @staticmethod
    def _format_frequency(frequency_hz: float) -> str:
        if frequency_hz >= 1000.0:
            return f"{frequency_hz / 1000.0:.1f} kHz"
        return f"{frequency_hz:.0f} Hz"

    def _axis_prefix(self) -> str:
        """Return the left padding needed to align the axis with bar columns."""
        return self._axis_padding() + " "

    @staticmethod
    def _axis_label_width() -> int:
        """Return the fixed width reserved for left-side axis labels."""
        return len(f"{0:>4} dB ")

    def _axis_padding(self) -> str:
        """Return blank padding up to the vertical axis separator column."""
        return " " * self._axis_label_width()

    def _axis_notch_columns(
        self,
        frequencies_hz: tuple[float, ...],
    ) -> set[int]:
        """Return horizontal-axis columns that should show label notches."""
        if not self._show_axis_labels or not frequencies_hz:
            return set()

        minimum = frequencies_hz[0]
        maximum = frequencies_hz[-1]
        return {
            self._frequency_to_column(minimum, maximum, marker_hz, self._graph_width)
            for marker_hz in self._select_axis_markers(frequencies_hz)
            if self._frequency_to_column(minimum, maximum, marker_hz, self._graph_width)
            > 0
        }

    def _build_frequency_axis_lines(
        self,
        frequencies_hz: tuple[float, ...],
        axis_prefix: str,
        total_graph_width: int,
    ) -> list[str]:
        """Build aligned label rows distributed across the axis width."""
        markers = self._select_axis_markers(frequencies_hz)
        if not frequencies_hz or not markers:
            return [axis_prefix + "0 Hz"]

        minimum = frequencies_hz[0]
        maximum = frequencies_hz[-1]

        label_rows = [[" "] * total_graph_width for _ in range(2)]
        overflow_suffixes = ["", ""]
        used_ranges: list[list[tuple[int, int]]] = [[], []]

        last_marker = markers[-1]
        for marker_hz in markers:
            is_terminal_marker = marker_hz == last_marker

            label = self._format_axis_label(
                marker_hz,
                is_terminal_marker=is_terminal_marker,
            )
            visible_label, overflow_suffix = self._split_axis_label(label)
            center = self._frequency_to_column(
                minimum,
                maximum,
                marker_hz,
                total_graph_width,
            )
            start = max(
                0,
                min(
                    center - (len(visible_label) // 2),
                    len(label_rows[0]) - len(visible_label),
                ),
            )
            end = start + len(visible_label)
            row_index = self._select_label_row(used_ranges, start, end)
            if row_index is None and is_terminal_marker:
                row_index = len(used_ranges) - 1
            if row_index is None:
                continue

            for offset, character in enumerate(visible_label):
                label_rows[row_index][start + offset] = character
            used_ranges[row_index].append((start, end))
            if is_terminal_marker:
                overflow_suffixes[row_index] = overflow_suffix

        return [
            axis_prefix
            + self._colorize(
                "".join(label_rows[0]).rstrip() + overflow_suffixes[0],
                self._label_color_code,
            ),
            axis_prefix
            + self._colorize(
                "".join(label_rows[1]).rstrip() + overflow_suffixes[1],
                self._label_color_code,
            ),
        ]

    @staticmethod
    def _split_axis_label(label: str) -> tuple[str, str]:
        """Split a terminal axis label so the final Hz suffix may overflow."""
        if label.endswith("Hz") and len(label) > 2:
            return label[:-2], label[-2:]
        return label, ""

    def _select_axis_markers(
        self,
        frequencies_hz: tuple[float, ...],
    ) -> list[float]:
        """Return marker frequencies that fit within the rendered band range."""
        if not frequencies_hz:
            return []

        minimum = frequencies_hz[0]
        maximum = frequencies_hz[-1]
        configured_markers = self._axis_frequencies or self._AXIS_MARKERS_HZ
        return [
            marker_hz
            for marker_hz in configured_markers
            if minimum <= marker_hz <= maximum
        ]

    @staticmethod
    def _select_label_row(
        used_ranges: list[list[tuple[int, int]]],
        start: int,
        end: int,
    ) -> int | None:
        """Choose a non-overlapping label row for the requested label span."""
        for row_index, row_ranges in enumerate(used_ranges):
            overlaps = any(
                not (end <= used_start or start >= used_end)
                for used_start, used_end in row_ranges
            )
            if not overlaps:
                return row_index
        return None

    @staticmethod
    def _nearest_frequency_index(
        frequencies_hz: tuple[float, ...],
        marker_hz: float,
    ) -> int:
        """Return the band index closest to the requested marker frequency."""
        return min(
            range(len(frequencies_hz)),
            key=lambda index: abs(
                math.log10(frequencies_hz[index]) - math.log10(marker_hz)
            ),
        )

    @staticmethod
    def _format_axis_label(
        frequency_hz: float,
        is_terminal_marker: bool = False,
    ) -> str:
        """Return a compact frequency label suitable for the axis label row."""
        if frequency_hz >= 1000.0:
            value = f"{frequency_hz / 1000.0:.0f}k"
        else:
            value = f"{frequency_hz:.0f}"
        if is_terminal_marker:
            return f"{value}Hz"
        return value

    def _build_band_columns(
        self,
        band_count: int,
        separator_columns: set[int],
    ) -> list[tuple[int, ...]]:
        """Return graph columns allocated to each band, skipping separator gaps."""
        if band_count <= 0:
            return []

        visible_columns = [
            column
            for column in range(self._graph_width)
            if column not in separator_columns
        ]

        bands: list[tuple[int, ...]] = []
        previous_end = 0
        for index in range(band_count):
            end = round((index + 1) * len(visible_columns) / band_count)
            bands.append(tuple(visible_columns[previous_end:end]))
            previous_end = end
        return bands

    def _separator_columns(
        self,
        frequencies_hz: tuple[float, ...],
    ) -> set[int]:
        """Return gap columns between neighboring labeled-frequency regions."""
        if self._band_gap <= 0 or not frequencies_hz:
            return set()

        minimum = frequencies_hz[0]
        maximum = frequencies_hz[-1]

        marker_columns = [
            self._frequency_to_column(
                minimum,
                maximum,
                marker_hz,
                self._graph_width,
            )
            for marker_hz in self._select_axis_markers(frequencies_hz)
        ]
        marker_columns = sorted(dict.fromkeys(marker_columns))

        separators: set[int] = set()
        half = self._band_gap // 2
        for left, right in zip(marker_columns, marker_columns[1:], strict=False):
            if right - left <= 1:
                continue
            midpoint = (left + right) // 2
            start = max(0, midpoint - half)
            end = min(self._graph_width, start + self._band_gap)
            separators.update(range(start, end))

        return separators

    @staticmethod
    def _apply_separators(
        row: list[str],
        separator_columns: frozenset[int] | set[int],
    ) -> None:
        """Apply vertical separators in-place by blanking target columns."""
        for column in separator_columns:
            if 0 <= column < len(row):
                row[column] = " "

    @staticmethod
    def _apply_axis_notches(
        row: list[str],
        notch_columns: frozenset[int] | set[int],
    ) -> None:
        """Apply horizontal-axis notch characters at labeled frequency columns."""
        for column in notch_columns:
            if 0 <= column < len(row):
                row[column] = AXIS_JUNCTION

    @staticmethod
    def _clear_color_codes(
        color_codes: list[str | None],
        separator_columns: set[int],
    ) -> None:
        """Disable coloring for columns that were turned into separators."""
        for column in separator_columns:
            if 0 <= column < len(color_codes):
                color_codes[column] = None

    def _serialize_bar_row(self, row: list[str], color_codes: list[str | None]) -> str:
        """Serialize a character row, applying ANSI color codes per contiguous run."""
        if not self.color_enabled:
            return "".join(row)

        if not color_codes or all(color_code is None for color_code in color_codes):
            return "".join(row)

        output: list[str] = []
        run_start = 0
        active_color = color_codes[0]
        for index in range(1, len(row) + 1):
            next_color = color_codes[index] if index < len(color_codes) else None
            if index < len(row) and next_color == active_color:
                continue

            text = "".join(row[run_start:index])
            if active_color is not None:
                output.append(active_color)
                output.append(text)
                output.append(RESET)
            else:
                output.append(text)

            run_start = index
            if index < len(color_codes):
                active_color = color_codes[index]

        return "".join(output)

    def _colorize(self, text: str, color_code: str | None) -> str:
        """Apply a single ANSI color code to full text when enabled."""
        if self.color_enabled and color_code is not None and text:
            return f"{color_code}{text}{RESET}"
        return text

    @staticmethod
    def _frequency_to_column(
        minimum_frequency_hz: float,
        maximum_frequency_hz: float,
        frequency_hz: float,
        total_graph_width: int,
    ) -> int:
        """Map a frequency to the closest graph column using log spacing."""
        if total_graph_width <= 1 or maximum_frequency_hz <= minimum_frequency_hz:
            return 0

        normalized = (
            math.log10(frequency_hz) - math.log10(minimum_frequency_hz)
        ) / (
            math.log10(maximum_frequency_hz) - math.log10(minimum_frequency_hz)
        )
        position = round(normalized * (total_graph_width - 1))
        return max(0, min(total_graph_width - 1, position))


def _default_graph_height(db_min: float, db_max: float, db_interval: float) -> int:
    """Return the legacy row count implied by the configured dB scale."""
    top = math.floor(db_max / db_interval) * db_interval
    row_count = 0
    current = top
    while current >= db_min - 1e-9:
        row_count += 1
        current = round(current - db_interval, 10)
    if row_count == 0 or abs(top - db_max) > 1e-9:
        row_count += 1
    return max(1, row_count)


def _build_row_thresholds(
    db_min: float,
    db_max: float,
    graph_height: int,
) -> list[float]:
    """Generate graph row thresholds from db_max down to db_min."""
    if graph_height <= 1:
        return [db_max]

    step = (db_max - db_min) / (graph_height - 1)
    return [round(db_max - (index * step), 10) for index in range(graph_height)]


def _build_db_marker_values(
    db_min: float,
    db_max: float,
    db_interval: float,
) -> list[float]:
    """Generate labeled dB marker values based on the configured interval."""
    top = math.floor(db_max / db_interval) * db_interval
    labels: list[float] = []
    current = top
    while current >= db_min - 1e-9:
        labels.append(current)
        current = round(current - db_interval, 10)
    if not labels or abs(labels[0] - db_max) > 1e-9:
        labels.insert(0, db_max)
    return labels


def _build_db_marker_labels(
    row_thresholds: list[float],
    db_min: float,
    db_max: float,
    db_interval: float,
) -> dict[int, str]:
    """Map dB interval markers to the nearest graph rows for labeling."""
    labels_by_row: dict[int, float] = {}
    for marker in _build_db_marker_values(db_min, db_max, db_interval):
        row_index = min(
            range(len(row_thresholds)),
            key=lambda index: abs(row_thresholds[index] - marker),
        )
        existing = labels_by_row.get(row_index)
        if existing is None or abs(row_thresholds[row_index] - marker) < abs(
            row_thresholds[row_index] - existing
        ):
            labels_by_row[row_index] = marker

    return {
        row_index: str(int(round(marker)))
        for row_index, marker in labels_by_row.items()
    }


def supports_color(is_a_tty: bool, term: str | None) -> bool:
    """Return whether ANSI color output should be enabled for the terminal."""
    if not is_a_tty:
        return False

    normalized_term = (term or "").strip().lower()
    if normalized_term == "dumb":
        return False

    if os.name == "nt":
        return _enable_windows_vt_mode()

    return normalized_term != ""


def _enable_windows_vt_mode() -> bool:
    """Best-effort enable ANSI color support for Windows console output."""
    try:
        import ctypes

        windll = cast(_WindowsDllLoader | None, getattr(ctypes, "windll", None))
        if windll is None:
            return False

        stdout_handle = windll.kernel32.GetStdHandle(-11)
        if stdout_handle in {0, -1}:
            return False

        console_mode = ctypes.c_uint32()
        if windll.kernel32.GetConsoleMode(
            stdout_handle,
            ctypes.byref(console_mode),
        ) == 0:
            return False

        enable_virtual_terminal_processing = 0x0004
        if console_mode.value & enable_virtual_terminal_processing:
            return True

        return bool(
            windll.kernel32.SetConsoleMode(
                stdout_handle,
                console_mode.value | enable_virtual_terminal_processing,
            )
            != 0
        )
    except Exception:
        return False
