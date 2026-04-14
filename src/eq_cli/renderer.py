from __future__ import annotations

import math
import os
from dataclasses import dataclass

RESET = "\x1b[0m"
CYAN = "\x1b[36m"
RED = "\x1b[31m"
AXIS_SEPARATOR = "|"
AXIS_JUNCTION = "+"

DB_MIN_DEFAULT = -80.0
DB_MAX_DEFAULT = 6.0
DB_INTERVAL_DEFAULT = 10.0
GRAPH_WIDTH_DEFAULT = 120
BAND_GAP_DEFAULT = 0
BAR_CHAR_DEFAULT = "#"
PEAK_CHAR_DEFAULT = "-"
DB_MARKER_STYLE_DEFAULT = "spaced"


@dataclass(frozen=True)
class RenderFrame:
    """A renderable snapshot of log-spaced spectrum levels."""

    frequencies_hz: tuple[float, ...]
    levels_db: tuple[float, ...]
    peak_levels_db: tuple[float, ...] | None = None
    history_levels_db: tuple[tuple[float, ...], ...] | None = None
    freeze_enabled: bool = False
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
        graph_width: int = GRAPH_WIDTH_DEFAULT,
        band_gap: int = BAND_GAP_DEFAULT,
        bar_char: str = BAR_CHAR_DEFAULT,
        peak_char: str = PEAK_CHAR_DEFAULT,
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
            graph_width=graph_width,
            band_gap=band_gap,
            bar_char=bar_char,
            peak_char=peak_char,
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
        graph_width: int = GRAPH_WIDTH_DEFAULT,
        band_gap: int = BAND_GAP_DEFAULT,
        bar_char: str = BAR_CHAR_DEFAULT,
        peak_char: str = PEAK_CHAR_DEFAULT,
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
        self._bar_char = bar_char
        self._peak_char = peak_char
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
        self._row_labels = _build_row_labels(db_min, db_max, db_interval)
        self._lines_rendered: int = 0

    def render(self, frame: RenderFrame) -> str:
        """Render a frame with dB rows, bars, and a frequency axis."""
        peak_markers = self._compute_peak_markers(frame)
        axis_prefix = self._axis_prefix()
        band_spans = self._build_band_spans(len(frame.levels_db))
        total_graph_width = self._total_graph_width(band_spans)
        separator_columns = self._separator_columns(frame.frequencies_hz, band_spans)
        lines: list[str] = []
        if self._show_title:
            centered_title = self._title_text.center(total_graph_width)
            lines.append(
                axis_prefix
                + self._colorize(centered_title, self._label_color_code)
            )

        for row_index, threshold in enumerate(self._row_labels):
            bars = self._build_bar_row(
                levels_db=frame.levels_db,
                threshold_db=threshold,
                peak_markers=peak_markers,
                band_spans=band_spans,
                total_width=total_graph_width,
                separator_columns=separator_columns,
            )
            label = (
                str(int(threshold))
                if threshold == int(threshold)
                else f"{threshold:.1f}"
            )
            prefix = self._format_row_prefix(label, row_index, len(self._row_labels))
            lines.append(prefix + bars)

        baseline = list("-" * total_graph_width)
        self._apply_separators(baseline, separator_columns)
        lines.append(
            self._axis_padding()
            + self._colorize(AXIS_JUNCTION, self._axis_color_code)
            + self._colorize("".join(baseline), self._axis_color_code)
        )
        if self._show_axis_labels:
            lines.extend(
                self._build_frequency_axis_lines(
                    frame.frequencies_hz,
                    axis_prefix,
                    band_spans,
                    total_graph_width,
                )
            )
        lines.extend(
            self._build_history_lines(
                frame=frame,
                band_spans=band_spans,
                total_graph_width=total_graph_width,
                separator_columns=separator_columns,
            )
        )
        if self._show_shortcuts:
            lines.append(
                axis_prefix
                + self._colorize(
                    self._shortcuts_line(frame.freeze_enabled),
                    self._label_color_code,
                )
            )
        output = "\n".join(lines) + "\n"
        prefix = f"\x1b[{self._lines_rendered}A" if self._lines_rendered > 0 else ""
        self._lines_rendered = len(lines)
        return prefix + output

    def _build_history_lines(
        self,
        frame: RenderFrame,
        band_spans: list[tuple[int, int]],
        total_graph_width: int,
        separator_columns: set[int],
    ) -> list[str]:
        """Render history rows as a lightweight waterfall under the axis."""
        if self._history_rows <= 0 or frame.history_levels_db is None:
            return []

        visible_history = frame.history_levels_db[-self._history_rows :]
        history_lines: list[str] = []
        for history_row in visible_history:
            row = [" "] * total_graph_width
            for level_db, (start, end) in zip(history_row, band_spans, strict=False):
                character = self._history_char(level_db)
                row[start:end] = [character] * max(0, end - start)
            self._apply_separators(row, separator_columns)
            history_lines.append(
                self._axis_padding()
                + self._colorize(AXIS_SEPARATOR, self._axis_color_code)
                + self._colorize("".join(row), self._history_color_code)
            )

        return history_lines

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
        return f"[F] Freeze: {freeze_text}  [R] Reset Peaks  [Q] Quit"

    def _format_row_prefix(
        self,
        label: str,
        row_index: int,
        total_rows: int,
    ) -> str:
        """Return the dB label/prefix for one rendered row."""
        marker_width = self._axis_label_width()
        if not self._show_axis_labels:
            return (
                f"{' ' * marker_width}"
                f"{self._colorize(AXIS_SEPARATOR, self._axis_color_code)}"
            )
        if not self._show_db_marker(row_index, total_rows):
            return (
                f"{' ' * marker_width}"
                f"{self._colorize(AXIS_SEPARATOR, self._axis_color_code)}"
            )

        marker = f"{label:>4} dB "
        return (
            self._colorize(marker, self._label_color_code)
            + self._colorize(AXIS_SEPARATOR, self._axis_color_code)
        )

    def _show_db_marker(self, row_index: int, total_rows: int) -> bool:
        """Return whether to show the row dB marker for the selected style."""
        if self._db_marker_style in {"all", "spaced"}:
            return True
        if row_index == 0 or row_index == total_rows - 1:
            return True
        midpoint = total_rows // 2
        return row_index == midpoint

    def _build_bar_row(
        self,
        levels_db: tuple[float, ...],
        threshold_db: float,
        peak_markers: set[tuple[int, float]],
        band_spans: list[tuple[int, int]],
        total_width: int,
        separator_columns: set[int],
    ) -> str:
        """Build a single rendered dB row including any configured inter-band gaps."""
        row = [" "] * total_width
        color_codes: list[str | None] = [None] * total_width
        for index, (level_db, (start, end)) in enumerate(
            zip(levels_db, band_spans, strict=False)
        ):
            segment, color_code = self._render_bar_segment(
                level_db=level_db,
                threshold_db=threshold_db,
                span_width=end - start,
                is_peak_row=(index, threshold_db) in peak_markers,
            )
            row[start:end] = list(segment)
            if color_code is not None:
                color_codes[start:end] = [color_code] * (end - start)

        self._apply_separators(row, separator_columns)
        self._clear_color_codes(color_codes, separator_columns)
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

    def _find_peak_row(self, peak_db: float) -> float:
        """Return the smallest row threshold at or above the peak level."""
        target = self._row_labels[0]
        for label in self._row_labels:
            if label >= peak_db:
                target = label
        return target

    def _render_bar_segment(
        self,
        level_db: float,
        threshold_db: float,
        span_width: int,
        is_peak_row: bool = False,
    ) -> tuple[str, str | None]:
        if span_width <= 0:
            return "", None
        if is_peak_row and level_db < threshold_db:
            return (
                self._peak_char * span_width,
                self._peak_color_code if self.color_enabled else None,
            )
        if level_db <= self._db_min:
            return " " * span_width, None
        if level_db < max(self._db_min, threshold_db):
            return " " * span_width, None
        return (
            self._bar_char * span_width,
            self._bar_color_code if self.color_enabled else None,
        )

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

    def _build_frequency_axis_lines(
        self,
        frequencies_hz: tuple[float, ...],
        axis_prefix: str,
        band_spans: list[tuple[int, int]],
        total_graph_width: int,
    ) -> list[str]:
        """Build aligned label rows distributed across the axis width."""
        if not frequencies_hz:
            return [axis_prefix + "0 Hz"]

        label_rows = [[" "] * total_graph_width for _ in range(2)]
        overflow_suffixes = ["", ""]
        used_ranges: list[list[tuple[int, int]]] = [[], []]

        for marker_hz in self._select_axis_markers(frequencies_hz):
            index = self._nearest_frequency_index(frequencies_hz, marker_hz)
            is_terminal_marker = marker_hz == frequencies_hz[-1]

            label = self._format_axis_label(
                marker_hz,
                is_terminal_marker=is_terminal_marker,
            )
            visible_label, overflow_suffix = self._split_axis_label(label)
            center = self._band_center(band_spans[index])
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
        minimum = frequencies_hz[0]
        maximum = frequencies_hz[-1]
        return [
            marker_hz
            for marker_hz in self._AXIS_MARKERS_HZ
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

    def _build_band_spans(self, band_count: int) -> list[tuple[int, int]]:
        """Return contiguous graph spans for each band across the target width."""
        if band_count <= 0:
            return []

        effective_width = max(self._graph_width, band_count)
        band_widths: list[int] = []
        previous_end = 0
        for index in range(band_count):
            end = round((index + 1) * effective_width / band_count)
            band_widths.append(end - previous_end)
            previous_end = end

        spans: list[tuple[int, int]] = []
        start = 0
        for band_width in band_widths:
            end = start + band_width
            spans.append((start, end))
            start = end
        return spans

    def _separator_columns(
        self,
        frequencies_hz: tuple[float, ...],
        band_spans: list[tuple[int, int]],
    ) -> set[int]:
        """Return gap columns between neighboring labeled-frequency regions."""
        if self._band_gap <= 0 or not frequencies_hz:
            return set()

        marker_columns = [
            self._band_center(
                band_spans[self._nearest_frequency_index(frequencies_hz, marker_hz)]
            )
            for marker_hz in self._select_axis_markers(frequencies_hz)
        ]

        separators: set[int] = set()
        half = self._band_gap // 2
        for left, right in zip(marker_columns, marker_columns[1:], strict=False):
            midpoint = (left + right) // 2
            start = max(0, midpoint - half)
            end = min(self._graph_width, start + self._band_gap)
            separators.update(range(start, end))

        return separators

    @staticmethod
    def _apply_separators(row: list[str], separator_columns: set[int]) -> None:
        """Apply vertical separators in-place by blanking target columns."""
        for column in separator_columns:
            if 0 <= column < len(row):
                row[column] = " "

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
        """Serialize a character row, applying ANSI color codes per cell."""
        output: list[str] = []
        for character, color_code in zip(row, color_codes, strict=False):
            if color_code is not None:
                output.append(f"{color_code}{character}{RESET}")
            else:
                output.append(character)
        return "".join(output)

    def _colorize(self, text: str, color_code: str | None) -> str:
        """Apply a single ANSI color code to full text when enabled."""
        if self.color_enabled and color_code is not None and text:
            return f"{color_code}{text}{RESET}"
        return text

    @staticmethod
    def _total_graph_width(band_spans: list[tuple[int, int]]) -> int:
        """Return the full horizontal width of the rendered graph including gaps."""
        if not band_spans:
            return 0
        return band_spans[-1][1]

    @staticmethod
    def _band_center(span: tuple[int, int]) -> int:
        """Return the center column of a band span."""
        start, end = span
        return start + max(0, (end - start - 1) // 2)


def _build_row_labels(
    db_min: float, db_max: float, db_interval: float
) -> list[float]:
    """Generate row threshold labels from db_max down to db_min."""
    top = math.floor(db_max / db_interval) * db_interval
    labels: list[float] = []
    current = top
    while current >= db_min - 1e-9:
        labels.append(current)
        current = round(current - db_interval, 10)
    if not labels or abs(labels[0] - db_max) > 1e-9:
        labels.insert(0, db_max)
    return labels


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

        stdout_handle = ctypes.windll.kernel32.GetStdHandle(-11)
        if stdout_handle in {0, -1}:
            return False

        console_mode = ctypes.c_uint32()
        if ctypes.windll.kernel32.GetConsoleMode(
            stdout_handle,
            ctypes.byref(console_mode),
        ) == 0:
            return False

        enable_virtual_terminal_processing = 0x0004
        if console_mode.value & enable_virtual_terminal_processing:
            return True

        return bool(
            ctypes.windll.kernel32.SetConsoleMode(
                stdout_handle,
                console_mode.value | enable_virtual_terminal_processing,
            )
            != 0
        )
    except Exception:
        return False
