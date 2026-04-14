from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from textwrap import dedent
from typing import Callable, cast

from eq_cli.app import create_app
from eq_cli.audio import AudioInputDevice, AudioInputDeviceProvider, SoundDeviceProvider
from eq_cli.loop import run_equalizer
from eq_cli.profile import list_builtin_profiles, load_profile, resolve_color_code

_MODE_PRESETS: dict[str, dict[str, object]] = {
    "studio": {
        "profile": "studio",
        "volume_mode": "absolute",
        "channel_mode": "sum",
        "peak_hold_frames": 12,
    },
    "live": {
        "profile": "default",
        "volume_mode": "relative",
        "channel_mode": "mono",
        "refresh_rate": 60.0,
        "peak_hold_frames": 4,
    },
    "debug": {
        "profile": "high-contrast",
        "volume_mode": "relative",
        "channel_mode": "sum",
        "history_rows": 6,
        "axis_labels": True,
        "db_marker_style": "all",
    },
}

_HELP_EPILOG = dedent(
    """
    Usability Tips:
      - Start quickly: eq-cli --device <id-or-name> --mode studio
      - Discover presets: eq-cli --list-profiles
      - Keep output compact: use --no-shortcuts and --history-rows 0
      - Tune readability: try --axis-labels with --db-marker-style minimal
      - Runtime keys: f=freeze, r=reset peaks, q=quit
    """
)

_HELP_DESCRIPTION = dedent(
    """
    Capture live audio from an input device and render a real-time spectrum in
    your terminal. Choose a profile or mode for quick defaults, then tune
    responsiveness and readability with options like refresh rate, axis labels,
    history rows, and color overrides.
    """
)


class DeviceSelectionError(Exception):
    """Raised when the requested audio input device cannot be resolved."""


class ProfileLoadError(Exception):
    """Raised when a requested profile cannot be loaded or parsed."""


def _resolve_device_by_reference(
    devices: list[AudioInputDevice],
    reference: str,
) -> AudioInputDevice:
    for device in devices:
        if reference in {device.identifier, device.name}:
            return device

    raise DeviceSelectionError(f"Unknown input device: {reference}")


def _prompt_for_device(
    devices: list[AudioInputDevice],
    input_func: Callable[[str], str],
) -> AudioInputDevice:
    print("Select an input device:")
    for index, device in enumerate(devices, start=1):
        print(f"{index}. {device.name} ({device.identifier})")

    selection = input_func("Enter device number: ").strip()
    if not selection:
        raise DeviceSelectionError("No device selection was provided.")

    if selection.isdigit():
        device_index = int(selection) - 1
        if 0 <= device_index < len(devices):
            return devices[device_index]
        raise DeviceSelectionError(f"Unknown input device selection: {selection}")

    return _resolve_device_by_reference(devices, selection)


def _list_devices(devices: list[AudioInputDevice]) -> None:
    for device in devices:
        marker = " * (default)" if device.is_default else ""
        print(f"{device.identifier}: {device.name}{marker}")


def _has_flag(arguments: Sequence[str], flags: tuple[str, ...]) -> bool:
    """Return whether any of the provided flags were passed by the user."""
    return any(flag in arguments for flag in flags)


def _apply_mode_defaults(
    args: argparse.Namespace,
    provided_args: Sequence[str],
) -> argparse.Namespace:
    """Apply mode-preset defaults, letting explicit flags keep precedence."""
    if args.mode is None:
        return args

    preset = _MODE_PRESETS[args.mode]

    if not _has_flag(provided_args, ("--profile", "--profile-file")):
        args.profile = str(preset["profile"])
    if not _has_flag(provided_args, ("--volume-mode",)):
        args.volume_mode = str(preset["volume_mode"])
    if not _has_flag(provided_args, ("--channel-mode",)):
        args.channel_mode = str(preset["channel_mode"])
    if not _has_flag(provided_args, ("--peak-hold-frames",)):
        args.peak_hold_frames = int(cast(int, preset["peak_hold_frames"]))
    if "history_rows" in preset and not _has_flag(provided_args, ("--history-rows",)):
        args.history_rows = int(cast(int, preset["history_rows"]))

    if "refresh_rate" in preset and not _has_flag(provided_args, ("--refresh-rate",)):
        args.refresh_rate = float(cast(float, preset["refresh_rate"]))
    if "axis_labels" in preset and not _has_flag(provided_args, ("--axis-labels",)):
        args.axis_labels = bool(cast(bool, preset["axis_labels"]))
    if "db_marker_style" in preset and not _has_flag(
        provided_args,
        ("--db-marker-style",),
    ):
        args.db_marker_style = str(preset["db_marker_style"])

    return args


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level command-line parser for the application."""
    app = create_app()
    parser = argparse.ArgumentParser(
        prog=app.name,
        description=_HELP_DESCRIPTION,
        epilog=_HELP_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--mode",
        choices=["studio", "live", "debug"],
        dest="mode",
        help="Apply a convenience preset mode (studio, live, or debug).",
    )
    parser.add_argument(
        "--list-profiles",
        action="store_true",
        help="List available built-in rendering profiles and exit.",
    )
    parser.add_argument(
        "--list-devices",
        action="store_true",
        help="List available audio input devices and exit.",
    )
    parser.add_argument(
        "--device",
        help="Select an audio input device by identifier or name.",
    )
    parser.add_argument(
        "--gain",
        type=float,
        default=0.0,
        metavar="DB",
        help="Additive dB offset applied to all display levels (default: 0).",
    )
    parser.add_argument(
        "--db-min",
        type=float,
        default=-80.0,
        dest="db_min",
        metavar="DB",
        help="Bottom of the dB display scale (default: -80).",
    )
    parser.add_argument(
        "--db-max",
        type=float,
        default=6.0,
        dest="db_max",
        metavar="DB",
        help="Top of the dB display scale (default: 6).",
    )
    parser.add_argument(
        "--db-interval",
        type=float,
        default=10.0,
        dest="db_interval",
        metavar="DB",
        help="Row spacing in dB (default: 10).",
    )
    parser.add_argument(
        "--volume-mode",
        choices=["relative", "absolute"],
        default="relative",
        dest="volume_mode",
        help="Volume mapping mode: relative (carved out) or absolute.",
    )
    parser.add_argument(
        "--channel-mode",
        choices=["mono", "left", "right", "sum", "mid", "side"],
        default="mono",
        dest="channel_mode",
        help="Channel analysis mode for mono/stereo input.",
    )
    parser.add_argument(
        "--refresh-rate",
        type=float,
        default=30.0,
        dest="refresh_rate",
        metavar="HZ",
        help="Maximum redraw rate in frames per second (default: 30).",
    )
    parser.add_argument(
        "--graph-width",
        type=int,
        default=120,
        dest="graph_width",
        metavar="CHARS",
        help="Width of the graph area in characters (default: 120).",
    )
    parser.add_argument(
        "--band-gap",
        type=int,
        default=0,
        dest="band_gap",
        metavar="CHARS",
        help=(
            "Separator width inserted between labeled frequency regions "
            "(default: 0)."
        ),
    )
    parser.add_argument(
        "--bar-char",
        default="#",
        dest="bar_char",
        metavar="CHAR",
        help="Character used to draw active bars (default: #).",
    )
    parser.add_argument(
        "--peak-char",
        default="-",
        dest="peak_char",
        metavar="CHAR",
        help="Character used to draw peak markers (default: -).",
    )
    parser.add_argument(
        "--peak-hold-frames",
        type=int,
        default=0,
        dest="peak_hold_frames",
        metavar="N",
        help="Frames to hold peak markers before decay (default: 0).",
    )
    parser.add_argument(
        "--history-rows",
        type=int,
        default=0,
        dest="history_rows",
        metavar="N",
        help="Number of history rows to render below the spectrum (default: 0).",
    )
    parser.add_argument(
        "--history-gradient",
        default=" .:-=+*#%@",
        dest="history_gradient",
        metavar="TEXT",
        help="Character gradient used for history rendering.",
    )
    parser.add_argument(
        "--profile-file",
        dest="profile_file",
        metavar="PATH",
        help=(
            "Optional path to a JSON file containing named rendering profiles. "
            "If omitted, built-in profiles are used."
        ),
    )
    parser.add_argument(
        "--profile",
        default="default",
        help=(
            "Named built-in profile or profile from --profile-file "
            f"(built-ins: {', '.join(list_builtin_profiles())})."
        ),
    )
    parser.add_argument(
        "--axis-labels",
        action="store_true",
        default=False,
        dest="axis_labels",
        help="Enable axis labels for frequency and dB scales (default: off).",
    )
    parser.add_argument(
        "--show-shortcuts",
        action="store_true",
        default=True,
        dest="show_shortcuts",
        help="Show runtime shortcuts/status line in the render output.",
    )
    parser.add_argument(
        "--no-shortcuts",
        action="store_false",
        dest="show_shortcuts",
        help="Hide runtime shortcuts/status line.",
    )
    parser.add_argument(
        "--db-marker-style",
        choices=["all", "spaced", "minimal"],
        default="spaced",
        dest="db_marker_style",
        help="dB marker density style (default: spaced).",
    )
    parser.add_argument(
        "--title",
        action="store_true",
        default=True,
        dest="title",
        help="Render a centered title line (default: on).",
    )
    parser.add_argument(
        "--no-title",
        action="store_false",
        dest="title",
        help="Disable the centered title line.",
    )
    parser.add_argument(
        "--title-text",
        dest="title_text",
        metavar="TEXT",
        help="Optional title text override.",
    )
    parser.add_argument(
        "--color-axis",
        dest="color_axis",
        metavar="COLOR",
        help="Axis color name or ANSI code (e.g., cyan or 36).",
    )
    parser.add_argument(
        "--color-label",
        dest="color_label",
        metavar="COLOR",
        help="Label/title color name or ANSI code (e.g., white or 37).",
    )
    parser.add_argument(
        "--color-bar",
        dest="color_bar",
        metavar="COLOR",
        help="Bar color name or ANSI code (e.g., cyan or 36).",
    )
    parser.add_argument(
        "--color-peak",
        dest="color_peak",
        metavar="COLOR",
        help="Peak color name or ANSI code (e.g., red or 31).",
    )
    parser.add_argument(
        "--color-history",
        dest="color_history",
        metavar="COLOR",
        help="History color name or ANSI code (e.g., yellow or 33).",
    )
    return parser


def _merge_profile_settings(
    args: argparse.Namespace,
    provided_args: Sequence[str],
) -> argparse.Namespace:
    """Apply built-in or file-based profile values when CLI args use defaults."""

    if args.peak_hold_frames < 0:
        raise ValueError("Peak hold frames must be zero or greater.")
    if args.history_rows < 0:
        raise ValueError("History rows must be zero or greater.")
    if args.history_gradient == "":
        raise ValueError("History gradient must not be empty.")

    try:
        profile = load_profile(args.profile_file, args.profile)
    except ValueError as exc:
        raise ProfileLoadError(str(exc)) from exc

    colors: dict[str, object] = {}
    colors_obj = profile.get("colors")
    if isinstance(colors_obj, dict):
        colors = cast(dict[str, object], colors_obj)

    if not _has_flag(provided_args, ("--db-min",)) and "db_min" in profile:
        args.db_min = float(profile["db_min"])
    if not _has_flag(provided_args, ("--db-max",)) and "db_max" in profile:
        args.db_max = float(profile["db_max"])
    if not _has_flag(provided_args, ("--db-interval",)) and "db_interval" in profile:
        args.db_interval = float(profile["db_interval"])
    if not _has_flag(provided_args, ("--volume-mode",)) and "volume_mode" in profile:
        args.volume_mode = str(profile["volume_mode"])
    if not _has_flag(provided_args, ("--channel-mode",)) and "channel_mode" in profile:
        args.channel_mode = str(profile["channel_mode"])
    if (
        not _has_flag(provided_args, ("--peak-hold-frames",))
        and "peak_hold_frames" in profile
    ):
        args.peak_hold_frames = int(profile["peak_hold_frames"])
    if not _has_flag(provided_args, ("--history-rows",)) and "history_rows" in profile:
        args.history_rows = int(profile["history_rows"])
    if (
        not _has_flag(provided_args, ("--history-gradient",))
        and "history_gradient" in profile
    ):
        args.history_gradient = str(profile["history_gradient"])
    if not _has_flag(provided_args, ("--graph-width",)) and "graph_width" in profile:
        args.graph_width = int(profile["graph_width"])
    if not _has_flag(provided_args, ("--band-gap",)) and "band_gap" in profile:
        args.band_gap = int(profile["band_gap"])
    if not _has_flag(provided_args, ("--bar-char",)) and "bar_char" in profile:
        args.bar_char = str(profile["bar_char"])
    if not _has_flag(provided_args, ("--peak-char",)) and "peak_char" in profile:
        args.peak_char = str(profile["peak_char"])
    if not _has_flag(provided_args, ("--axis-labels",)) and "axis_labels" in profile:
        args.axis_labels = bool(profile["axis_labels"])
    if (
        not _has_flag(provided_args, ("--show-shortcuts", "--no-shortcuts"))
        and "show_shortcuts" in profile
    ):
        args.show_shortcuts = bool(profile["show_shortcuts"])
    if not _has_flag(provided_args, ("--title", "--no-title")) and "title" in profile:
        args.title = bool(profile["title"])
    if not _has_flag(provided_args, ("--title-text",)) and "title_text" in profile:
        args.title_text = str(profile["title_text"])
    if (
        not _has_flag(provided_args, ("--db-marker-style",))
        and "db_marker_style" in profile
    ):
        args.db_marker_style = str(profile["db_marker_style"])

    if not _has_flag(provided_args, ("--color-axis",)) and "axis" in colors:
        args.color_axis = str(colors["axis"])
    if not _has_flag(provided_args, ("--color-label",)) and "label" in colors:
        args.color_label = str(colors["label"])
    if not _has_flag(provided_args, ("--color-bar",)) and "bar" in colors:
        args.color_bar = str(colors["bar"])
    if not _has_flag(provided_args, ("--color-peak",)) and "peak" in colors:
        args.color_peak = str(colors["peak"])
    if not _has_flag(provided_args, ("--color-history",)) and "history" in colors:
        args.color_history = str(colors["history"])

    return args


def main(
    argv: Sequence[str] | None = None,
    device_provider: AudioInputDeviceProvider | None = None,
    input_func: Callable[[str], str] = input,
    loop_func: Callable[[AudioInputDevice], int] | None = None,
) -> int:
    """Run the CLI entrypoint.

    Args:
        argv: Optional command-line arguments excluding the executable name.
        device_provider: Optional provider used to discover audio input devices.
        input_func: Callable used to prompt for interactive input.
        loop_func: Callable used to start the equalizer render loop.

    Returns:
        Process exit code.
    """
    app = create_app()
    parser = build_parser()

    parsed_argv = list(argv) if argv is not None else list(sys.argv[1:])

    try:
        args = parser.parse_args(parsed_argv)
    except SystemExit as exc:
        if exc.code == 0:
            return 0
        raise

    if args.list_profiles:
        for profile_name in list_builtin_profiles():
            print(profile_name)
        return 0

    provider = device_provider or SoundDeviceProvider()

    try:
        args = _apply_mode_defaults(args, parsed_argv)
        args = _merge_profile_settings(args, parsed_argv)

        devices = provider.list_input_devices()
        if args.list_devices:
            _list_devices(devices)
            return 0

        if not devices:
            raise DeviceSelectionError("No audio input devices are available.")

        selected_device = (
            _resolve_device_by_reference(devices, args.device)
            if args.device
            else _prompt_for_device(devices, input_func)
        )
    except (DeviceSelectionError, ProfileLoadError, RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(
        f"Selected input device: {selected_device.name} "
        f"({selected_device.identifier})"
    )
    print(
        "Render settings: "
        f"profile={args.profile}, "
        f"mode={args.mode or 'custom'}, "
        f"volume_mode={args.volume_mode}, "
        f"channel_mode={args.channel_mode}, "
        f"peak_hold_frames={args.peak_hold_frames}, "
        f"history_rows={args.history_rows}, "
        f"history_gradient={args.history_gradient}, "
        f"refresh_rate={args.refresh_rate}"
    )
    _loop = loop_func if loop_func is not None else (
        lambda dev: run_equalizer(
            dev,
            gain_db=args.gain,
            db_min=args.db_min,
            db_max=args.db_max,
            db_interval=args.db_interval,
            volume_mode=args.volume_mode,
            channel_mode=args.channel_mode,
            refresh_rate=args.refresh_rate,
            graph_width=args.graph_width,
            band_gap=args.band_gap,
            bar_char=args.bar_char,
            peak_char=args.peak_char,
            peak_hold_frames=args.peak_hold_frames,
            history_rows=args.history_rows,
            history_gradient=args.history_gradient,
            show_shortcuts=args.show_shortcuts,
            show_axis_labels=args.axis_labels,
            show_title=args.title,
            title_text=args.title_text or f"{app.name} v{app.version}",
            db_marker_style=args.db_marker_style,
            bar_color_code=resolve_color_code(args.color_bar) or "\x1b[36m",
            peak_color_code=resolve_color_code(args.color_peak) or "\x1b[31m",
            history_color_code=resolve_color_code(args.color_history),
            axis_color_code=resolve_color_code(args.color_axis),
            label_color_code=resolve_color_code(args.color_label),
        )
    )
    return _loop(selected_device)


def run() -> None:
    """Execute the CLI and exit with the resulting status code."""
    raise SystemExit(main())
