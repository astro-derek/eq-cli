from __future__ import annotations

import os
import queue
import select
import sys
import time
from collections import deque
from typing import Literal

import numpy as np
import numpy.typing as npt
import sounddevice as sd  # type: ignore[import-untyped]

from eq_cli.audio import AudioInputDevice
from eq_cli.peaks import PeakTracker
from eq_cli.renderer import RenderFrame, TerminalRenderer
from eq_cli.spectrum import AudioFrame, SpectrumProcessor

SAMPLE_RATE = 48_000
BLOCK_SIZE = 4_096
BAND_COUNT = 64
DEFAULT_REFRESH_RATE = 30.0

_HIDE_CURSOR = "\x1b[?25l"
_SHOW_CURSOR = "\x1b[?25h"

HotkeyAction = Literal["none", "toggle_freeze", "reset_peaks", "quit"]
ChannelMode = Literal["mono", "left", "right", "sum", "mid", "side"]


def interpret_hotkey(key: str | None) -> HotkeyAction:
    """Map a raw key press to a loop action."""
    if key is None:
        return "none"
    normalized = key.strip().lower()
    if normalized == "f":
        return "toggle_freeze"
    if normalized == "r":
        return "reset_peaks"
    if normalized == "q":
        return "quit"
    return "none"


def _save_posix_terminal() -> list[object] | None:
    """Put stdin into cbreak mode and return saved attrs, or None if unavailable."""
    if os.name == "nt" or not sys.stdin.isatty():
        return None
    try:
        import termios
        import tty
    except ImportError:
        return None
    fd = sys.stdin.fileno()
    saved: list[object] = termios.tcgetattr(fd)  # type: ignore[attr-defined]
    tty.setcbreak(fd)  # type: ignore[attr-defined]
    return saved


def _restore_posix_terminal(saved: list[object] | None) -> None:
    """Restore terminal attrs previously saved by _save_posix_terminal."""
    if saved is None:
        return
    try:
        import termios
    except ImportError:
        return
    try:
        termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, saved)  # type: ignore[attr-defined]
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
        if not msvcrt.kbhit():
            return None
        character = msvcrt.getwch()
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


def run_equalizer(
    device: AudioInputDevice,
    gain_db: float = 0.0,
    db_min: float = -80.0,
    db_max: float = 6.0,
    db_interval: float = 10.0,
    volume_mode: Literal["relative", "absolute"] = "relative",
    channel_mode: ChannelMode = "mono",
    refresh_rate: float = DEFAULT_REFRESH_RATE,
    graph_width: int = 120,
    band_gap: int = 0,
    bar_char: str = "#",
    peak_char: str = "-",
    peak_hold_frames: int = 0,
    history_rows: int = 0,
    history_gradient: str = " .:-=+*#%@",
    show_shortcuts: bool = True,
    show_axis_labels: bool = False,
    show_title: bool = True,
    title_text: str | None = None,
    db_marker_style: Literal["all", "spaced", "minimal"] = "spaced",
    bar_color_code: str = "\x1b[36m",
    peak_color_code: str = "\x1b[31m",
    history_color_code: str | None = None,
    axis_color_code: str | None = None,
    label_color_code: str | None = None,
) -> int:
    """Start the real-time equalizer render loop for the selected input device.

    Args:
        device: The audio input device to capture from.
        gain_db: Additive dB offset applied to all display levels.
        db_min: Bottom of the displayed dB scale.
        db_max: Top of the displayed dB scale.
        db_interval: Row spacing in dB.
        volume_mode: Volume mapping mode ('relative' or 'absolute').
        channel_mode: Input channel analysis mode.
        refresh_rate: Maximum redraw rate in frames per second.
        graph_width: Width of the rendered graph area in characters.
        band_gap: Number of spaces inserted between adjacent bands.
        bar_char: Character used to draw active bars.
        peak_char: Character used to draw peak markers.
        peak_hold_frames: Frames to hold peaks before decay.
        history_rows: Number of history rows to render below the spectrum.
        history_gradient: Character gradient used for history rendering.
        show_shortcuts: Whether to render the runtime shortcuts/status line.
        show_axis_labels: Whether to render dB/frequency axis labels.
        show_title: Whether to render a centered title row.
        title_text: Optional title text. Defaults to renderer fallback.
        db_marker_style: dB marker style ('all', 'spaced', or 'minimal').
        bar_color_code: ANSI color for active bars.
        peak_color_code: ANSI color for peak markers.
        history_color_code: Optional ANSI color for history rows.
        axis_color_code: Optional ANSI color for axis baseline.
        label_color_code: Optional ANSI color for axis labels/title.

    Returns:
        Process exit code.
    """
    device_index: int | None = (
        int(device.identifier) if device.identifier.isdigit() else None
    )
    if refresh_rate <= 0.0:
        raise ValueError("Refresh rate must be greater than zero.")
    if history_rows < 0:
        raise ValueError("History rows must be zero or greater.")
    stream_channels = 1 if channel_mode in {"mono", "left"} else 2

    stream_block_size = max(128, int(SAMPLE_RATE / refresh_rate))
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
