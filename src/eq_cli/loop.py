from __future__ import annotations

import json
import os
import queue
import re
import select
import sys
import time
from collections import deque
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Protocol, TypeAlias, cast

import numpy as np
import numpy.typing as npt

from eq_cli.audio import AudioInputDevice
from eq_cli.peaks import PeakTracker
from eq_cli.profile import RenderProfile
from eq_cli.renderer import RenderFrame, TerminalRenderer
from eq_cli.spectrum import AudioFrame, SpectrumProcessor

SAMPLE_RATE = 48_000
BLOCK_SIZE = 4_096
BAND_COUNT = 64
DEFAULT_REFRESH_RATE = 30.0

_HIDE_CURSOR = "\x1b[?25l"
_SHOW_CURSOR = "\x1b[?25h"

HotkeyAction = Literal[
    "none",
    "toggle_freeze",
    "reset_peaks",
    "snapshot",
    "export_profile",
    "quit",
]
ChannelMode = Literal["mono", "left", "right", "sum", "mid", "side"]
TerminalAttributeValue: TypeAlias = int | bytes
TerminalAttributes: TypeAlias = list[int | list[TerminalAttributeValue]]


class _MsvcrtModule(Protocol):
    """Subset of the Windows keyboard API used by the input loop."""

    def kbhit(self) -> bool:
        """Return whether a keyboard event is waiting."""

    def getwch(self) -> str:
        """Return the next wide character from the console."""


def interpret_hotkey(key: str | None) -> HotkeyAction:
    """Map a raw key press to a loop action."""
    if key is None:
        return "none"
    normalized = key.strip().lower()
    if normalized == "f":
        return "toggle_freeze"
    if normalized == "r":
        return "reset_peaks"
    if normalized == "s":
        return "snapshot"
    if normalized == "p":
        return "export_profile"
    if normalized == "q":
        return "quit"
    return "none"


def _sanitize_snapshot_fragment(value: str) -> str:
    """Return an ASCII-safe filename fragment for snapshot naming."""
    sanitized = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip().lower())
    sanitized = sanitized.strip("-.")
    return sanitized or "chart"


def _save_snapshot(
    renderer: TerminalRenderer,
    frame: RenderFrame,
    snapshot_format: Literal["txt", "ansi"],
    snapshot_file: str | None,
    snapshot_dir: str | None,
    title_text: str,
) -> Path:
    """Serialize and write a snapshot to disk, returning the saved path."""
    if snapshot_file is not None:
        snapshot_path = Path(snapshot_file)
    else:
        base_dir = Path(snapshot_dir) if snapshot_dir is not None else Path.cwd()
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        title_fragment = _sanitize_snapshot_fragment(title_text)
        frozen_suffix = "-frozen" if frame.freeze_enabled else ""
        snapshot_path = base_dir / (
            f"eq-cli-snapshot-{timestamp}-{title_fragment}{frozen_suffix}."
            f"{snapshot_format}"
        )

    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_text = renderer.render_snapshot(frame, snapshot_format=snapshot_format)
    snapshot_path.write_text(snapshot_text, encoding="utf-8")
    return snapshot_path


def _next_profile_export_path(base_dir: Path) -> Path:
    """Return the next numbered profile export path inside the target folder."""
    index = 1
    while True:
        candidate = base_dir / f"eq-cli-profile-{index:03d}.json"
        if not candidate.exists():
            return candidate
        index += 1


def _save_profile_export(
    export_profile: RenderProfile,
    export_dir: str | None = None,
) -> Path:
    """Serialize and write the current effective profile settings to disk."""
    base_dir = Path(export_dir) if export_dir is not None else Path.cwd()
    base_dir.mkdir(parents=True, exist_ok=True)
    export_path = _next_profile_export_path(base_dir)
    payload = {"profiles": {export_path.stem: export_profile}}
    export_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return export_path


def _save_posix_terminal() -> TerminalAttributes | None:
    """Put stdin into cbreak mode and return saved attrs, or None if unavailable."""
    if os.name == "nt" or not sys.stdin.isatty():
        return None
    try:
        import termios
        import tty
    except ImportError:
        return None
    fd = sys.stdin.fileno()
    saved = cast(TerminalAttributes, termios.tcgetattr(fd))
    tty.setcbreak(fd)
    return saved


def _restore_posix_terminal(saved: TerminalAttributes | None) -> None:
    """Restore terminal attrs previously saved by _save_posix_terminal."""
    if saved is None:
        return
    try:
        import termios
    except ImportError:
        return
    try:
        termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, saved)
    except OSError:
        pass


def _read_hotkey() -> str | None:
    """Return a non-blocking single-key input on Windows or POSIX TTYs."""
    if not sys.stdin.isatty():
        return None
    if os.name == "nt":
        try:
            import msvcrt
        except ImportError:
            return None
        msvcrt_module = cast(_MsvcrtModule, msvcrt)
        if not msvcrt_module.kbhit():
            return None
        character = msvcrt_module.getwch()
        return character if isinstance(character, str) else None
    # POSIX: non-blocking check via select then read one char.
    try:
        ready, _, _ = select.select([sys.stdin], [], [], 0)
        if not ready:
            return None
        return sys.stdin.read(1)
    except OSError:
        return None


def extract_channel_samples(
    indata: npt.NDArray[np.float32],
    channel_mode: ChannelMode,
) -> npt.NDArray[np.float64]:
    """Extract a mono analysis signal from mono/stereo input according to mode."""
    if indata.ndim != 2 or indata.shape[1] <= 0:
        raise ValueError("Input data must have shape (frames, channels).")

    channels = indata.shape[1]
    left = indata[:, 0].astype(np.float64)

    if channels == 1:
        if channel_mode in {"mono", "left", "sum", "mid"}:
            return left
        raise ValueError("Selected channel mode requires stereo input.")

    right = indata[:, 1].astype(np.float64)
    if channel_mode == "left":
        return left
    if channel_mode == "right":
        return right
    if channel_mode in {"mono", "sum", "mid"}:
        return (left + right) / 2.0
    if channel_mode == "side":
        return (left - right) / 2.0

    raise ValueError(f"Unsupported channel mode: {channel_mode}")


@dataclass(frozen=True)
class RenderConfig:
    """All display and rendering parameters for the equalizer render loop.

    Grouping these into a dataclass replaces the previous 33-parameter
    ``run_equalizer`` signature, making call sites explicit and extensible.
    """

    gain_db: float = 0.0
    db_min: float = -80.0
    db_max: float = 6.0
    db_interval: float = 10.0
    graph_height: int = 0
    volume_mode: Literal["relative", "absolute"] = "relative"
    channel_mode: ChannelMode = "mono"
    refresh_rate: float = DEFAULT_REFRESH_RATE
    block_size: int | None = None
    graph_width: int = 120
    band_gap: int = 0
    axis_frequencies: Sequence[float] | None = None
    bar_char: str = "#"
    peak_char: str = "-"
    peak_db_labels: bool = False
    peak_hold_frames: int = 0
    history_rows: int = 0
    history_gradient: str = " .:-=+*#%@"
    show_shortcuts: bool = True
    show_axis_labels: bool = False
    show_title: bool = True
    title_text: str | None = None
    db_marker_style: Literal["all", "spaced", "minimal"] = "spaced"
    bar_color_code: str = "\x1b[36m"
    peak_color_code: str = "\x1b[31m"
    history_color_code: str | None = None
    axis_color_code: str | None = None
    label_color_code: str | None = None
    snapshot_file: str | None = None
    snapshot_format: Literal["txt", "ansi"] = "txt"
    snapshot_dir: str | None = None
    export_profile: RenderProfile | None = field(default=None)


def run_equalizer(
    device: AudioInputDevice,
    config: RenderConfig | None = None,
) -> int:
    """Start the real-time equalizer render loop for the selected input device.

    Args:
        device: The audio input device to capture from.
        config: Rendering and display parameters. Defaults to ``RenderConfig()``
            if not provided.

    Returns:
        Process exit code.
    """
    import sounddevice as sd  # type: ignore[import-untyped]

    if config is None:
        config = RenderConfig()

    # Unpack config fields into local names for readability inside the loop.
    gain_db = config.gain_db
    db_min = config.db_min
    db_max = config.db_max
    db_interval = config.db_interval
    graph_height = config.graph_height
    volume_mode = config.volume_mode
    channel_mode = config.channel_mode
    refresh_rate = config.refresh_rate
    block_size = config.block_size
    graph_width = config.graph_width
    band_gap = config.band_gap
    axis_frequencies = config.axis_frequencies
    bar_char = config.bar_char
    peak_char = config.peak_char
    peak_db_labels = config.peak_db_labels
    peak_hold_frames = config.peak_hold_frames
    history_rows = config.history_rows
    history_gradient = config.history_gradient
    show_shortcuts = config.show_shortcuts
    show_axis_labels = config.show_axis_labels
    show_title = config.show_title
    title_text = config.title_text
    db_marker_style = config.db_marker_style
    bar_color_code = config.bar_color_code
    peak_color_code = config.peak_color_code
    history_color_code = config.history_color_code
    axis_color_code = config.axis_color_code
    label_color_code = config.label_color_code
    snapshot_file = config.snapshot_file
    snapshot_format = config.snapshot_format
    snapshot_dir = config.snapshot_dir
    export_profile = config.export_profile

    device_index: int | None = (
        int(device.identifier) if device.identifier.isdigit() else None
    )
    if graph_height < 0:
        raise ValueError("Graph height must be zero or greater.")
    if refresh_rate <= 0.0:
        raise ValueError("Refresh rate must be greater than zero.")
    if block_size is not None and block_size <= 0:
        raise ValueError("Block size must be greater than zero.")
    if history_rows < 0:
        raise ValueError("History rows must be zero or greater.")
    stream_channels = 1 if channel_mode in {"mono", "left"} else 2

    stream_block_size = block_size or max(128, int(SAMPLE_RATE / refresh_rate))
    render_period = 1.0 / refresh_rate

    frame_queue: queue.Queue[npt.NDArray[np.float64]] = queue.Queue(maxsize=4)

    def _audio_callback(
        indata: npt.NDArray[np.float32],
        frames: int,
        time_info: object,
        status: sd.CallbackFlags,
    ) -> None:
        try:
            samples = extract_channel_samples(indata, channel_mode)
            frame_queue.put_nowait(samples)
        except queue.Full:
            pass
        except ValueError:
            pass

    processor = SpectrumProcessor(
        sample_rate=SAMPLE_RATE,
        band_count=BAND_COUNT,
        volume_mode=volume_mode,
    )
    tracker = PeakTracker(
        band_count=BAND_COUNT,
        hold_frames=peak_hold_frames,
        max_db=db_max,
        floor_db=db_min,
    )
    renderer = TerminalRenderer.auto(
        is_a_tty=sys.stdout.isatty(),
        term=os.environ.get("TERM"),
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

    saved_terminal = _save_posix_terminal()
    sys.stdout.write(_HIDE_CURSOR)
    sys.stdout.flush()

    try:
        with sd.InputStream(
            device=device_index,
            channels=stream_channels,
            samplerate=SAMPLE_RATE,
            blocksize=stream_block_size,
            dtype="float32",
            callback=_audio_callback,
        ):
            latest_frame: RenderFrame | None = None
            next_render_time = time.perf_counter()
            frozen = False
            history: deque[tuple[float, ...]] = deque(maxlen=history_rows)

            while True:
                action = interpret_hotkey(_read_hotkey())
                if action == "quit":
                    break
                if action == "toggle_freeze":
                    frozen = not frozen
                    if latest_frame is not None:
                        latest_frame = RenderFrame(
                            frequencies_hz=latest_frame.frequencies_hz,
                            levels_db=latest_frame.levels_db,
                            peak_levels_db=latest_frame.peak_levels_db,
                            history_levels_db=latest_frame.history_levels_db,
                            freeze_enabled=frozen,
                        )
                elif action == "reset_peaks":
                    tracker.reset()
                    if latest_frame is not None:
                        latest_frame = RenderFrame(
                            frequencies_hz=latest_frame.frequencies_hz,
                            levels_db=latest_frame.levels_db,
                            peak_levels_db=tuple(
                                [db_min] * len(latest_frame.levels_db)
                            ),
                            history_levels_db=latest_frame.history_levels_db,
                            freeze_enabled=frozen,
                        )
                elif action == "snapshot" and latest_frame is not None:
                    _save_snapshot(
                        renderer=renderer,
                        frame=latest_frame,
                        snapshot_format=snapshot_format,
                        snapshot_file=None,
                        snapshot_dir=snapshot_dir,
                        title_text=title_text or "eq-cli",
                    )
                elif action == "export_profile" and export_profile is not None:
                    _save_profile_export(export_profile)

                try:
                    raw = frame_queue.get(timeout=0.02)
                except queue.Empty:
                    raw = None

                if raw is not None and not frozen:
                    # Keep only the newest available frame to reduce visual latency.
                    while True:
                        try:
                            raw = frame_queue.get_nowait()
                        except queue.Empty:
                            break

                    bands = processor.process_frame(
                        AudioFrame(samples=raw, sample_rate=SAMPLE_RATE)
                    )
                    display_levels = tuple(
                        min(db_max, max(db_min, level + gain_db))
                        for level in bands.levels_db
                    )
                    if history_rows > 0:
                        history.append(display_levels)
                    peaks = tracker.update(display_levels)
                    latest_frame = RenderFrame(
                        frequencies_hz=bands.frequencies_hz,
                        levels_db=display_levels,
                        peak_levels_db=peaks,
                        history_levels_db=tuple(history) if history_rows > 0 else None,
                        freeze_enabled=frozen,
                    )

                    if snapshot_file is not None:
                        saved_path = _save_snapshot(
                            renderer=renderer,
                            frame=latest_frame,
                            snapshot_format=snapshot_format,
                            snapshot_file=snapshot_file,
                            snapshot_dir=snapshot_dir,
                            title_text=title_text or "eq-cli",
                        )
                        print(f"Saved snapshot: {saved_path}")
                        return 0

                now = time.perf_counter()
                if latest_frame is not None and now >= next_render_time:
                    sys.stdout.write(renderer.render(latest_frame))
                    sys.stdout.flush()
                    next_render_time = now + render_period

    except KeyboardInterrupt:
        pass
    except Exception as exc:
        sys.stderr.write(f"\nError: {exc}\n")
        return 1
    finally:
        _restore_posix_terminal(saved_terminal)
        sys.stdout.write(_SHOW_CURSOR + "\n")
        sys.stdout.flush()

    return 0
