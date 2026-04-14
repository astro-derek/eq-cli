from __future__ import annotations

import json
from pathlib import Path
from typing import TypedDict, cast

_BUILTIN_PROFILES: dict[str, "RenderProfile"] = {
    "default": {
        "volume_mode": "relative",
        "channel_mode": "mono",
        "peak_hold_frames": 0,
        "history_rows": 0,
        "history_gradient": " .:-=+*#%@",
        "db_min": -80.0,
        "db_max": 6.0,
        "db_interval": 10.0,
        "graph_width": 120,
        "band_gap": 0,
        "bar_char": "#",
        "peak_char": "-",
        "axis_labels": False,
        "show_shortcuts": True,
        "title": True,
        "db_marker_style": "spaced",
        "colors": {"bar": "cyan", "peak": "red"},
    },
    "studio": {
        "volume_mode": "absolute",
        "channel_mode": "sum",
        "peak_hold_frames": 12,
        "history_rows": 6,
        "history_gradient": " .:-=+*#%@",
        "db_min": -70.0,
        "db_max": 6.0,
        "db_interval": 6.0,
        "graph_width": 120,
        "band_gap": 1,
        "bar_char": "=",
        "peak_char": "^",
        "axis_labels": True,
        "show_shortcuts": True,
        "title": True,
        "title_text": "eq-cli studio",
        "db_marker_style": "minimal",
        "colors": {
            "axis": "bright_black",
            "label": "bright_white",
            "bar": "green",
            "peak": "bright_red",
        },
    },
    "green-based": {
        "volume_mode": "relative",
        "channel_mode": "mono",
        "peak_hold_frames": 6,
        "history_rows": 6,
        "history_gradient": " .:-=+*#%@",
        "db_min": -80.0,
        "db_max": 6.0,
        "db_interval": 10.0,
        "graph_width": 120,
        "band_gap": 1,
        "bar_char": "#",
        "peak_char": "*",
        "axis_labels": True,
        "show_shortcuts": True,
        "title": True,
        "title_text": "eq-cli green-based",
        "db_marker_style": "spaced",
        "colors": {
            "axis": "bright_green",
            "label": "green",
            "bar": "green",
            "peak": "bright_green",
            "history": "bright_green",
        },
    },
    "minimal": {
        "volume_mode": "relative",
        "channel_mode": "mono",
        "peak_hold_frames": 0,
        "history_rows": 0,
        "history_gradient": " .:-=+*#%@",
        "db_min": -80.0,
        "db_max": 0.0,
        "db_interval": 20.0,
        "graph_width": 100,
        "band_gap": 0,
        "bar_char": "|",
        "peak_char": ".",
        "axis_labels": False,
        "show_shortcuts": False,
        "title": False,
        "db_marker_style": "minimal",
        "colors": {"bar": "white", "peak": "bright_white"},
    },
    "high-contrast": {
        "volume_mode": "relative",
        "channel_mode": "sum",
        "peak_hold_frames": 4,
        "history_rows": 6,
        "history_gradient": " .:-=+*#%@",
        "db_min": -80.0,
        "db_max": 6.0,
        "db_interval": 10.0,
        "graph_width": 120,
        "band_gap": 1,
        "bar_char": "#",
        "peak_char": "*",
        "axis_labels": True,
        "show_shortcuts": True,
        "title": True,
        "title_text": "eq-cli high-contrast",
        "db_marker_style": "all",
        "colors": {
            "axis": "bright_white",
            "label": "bright_yellow",
            "bar": "bright_cyan",
            "peak": "bright_red",
        },
    },
}

_PROFILE_NUMERIC_KEYS = {"db_min", "db_max", "db_interval"}
_PROFILE_INTEGER_KEYS = {
    "graph_width",
    "band_gap",
    "peak_hold_frames",
    "history_rows",
}
_PROFILE_BOOLEAN_KEYS = {"axis_labels", "show_shortcuts", "title"}
_PROFILE_STRING_KEYS = {
    "title_text",
    "db_marker_style",
    "volume_mode",
    "channel_mode",
    "history_gradient",
}
_PROFILE_CHAR_KEYS = {"bar_char", "peak_char"}
_PROFILE_COLOR_KEYS = {"axis", "label", "bar", "peak", "history"}
_PROFILE_KEYS = (
    _PROFILE_NUMERIC_KEYS
    | _PROFILE_INTEGER_KEYS
    | _PROFILE_BOOLEAN_KEYS
    | _PROFILE_STRING_KEYS
    | _PROFILE_CHAR_KEYS
    | {"colors"}
)

_COLOR_MAP: dict[str, str] = {
    "black": "\x1b[30m",
    "red": "\x1b[31m",
    "green": "\x1b[32m",
    "yellow": "\x1b[33m",
    "blue": "\x1b[34m",
    "magenta": "\x1b[35m",
    "cyan": "\x1b[36m",
    "white": "\x1b[37m",
    "bright_black": "\x1b[90m",
    "bright_red": "\x1b[91m",
    "bright_green": "\x1b[92m",
    "bright_yellow": "\x1b[93m",
    "bright_blue": "\x1b[94m",
    "bright_magenta": "\x1b[95m",
    "bright_cyan": "\x1b[96m",
    "bright_white": "\x1b[97m",
}


class ThemeColors(TypedDict, total=False):
    """Color settings for themed renderer output."""

    axis: str
    label: str
    bar: str
    peak: str
    history: str


class RenderProfile(TypedDict, total=False):
    """Optional profile settings loaded from a profile file."""

    db_min: float
    db_max: float
    db_interval: float
    graph_width: int
    band_gap: int
    bar_char: str
    peak_char: str
    peak_hold_frames: int
    history_rows: int
    axis_labels: bool
    show_shortcuts: bool
    title: bool
    title_text: str
    volume_mode: str
    channel_mode: str
    history_gradient: str
    db_marker_style: str
    colors: ThemeColors


def list_builtin_profiles() -> tuple[str, ...]:
    """Return the names of bundled profiles available without a profile file."""
    return tuple(sorted(_BUILTIN_PROFILES))


def _validate_bool(value: object, label: str) -> bool:
    """Validate a boolean profile field."""
    if not isinstance(value, bool):
        raise ValueError(f"{label} must be a boolean.")
    return value


def _validate_number(value: object, label: str) -> float:
    """Validate a numeric profile field."""
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{label} must be a number.")
    return float(value)


def _validate_int(value: object, label: str) -> int:
    """Validate an integer profile field."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{label} must be an integer.")
    return value


def _validate_string(value: object, label: str) -> str:
    """Validate a string profile field."""
    if not isinstance(value, str):
        raise ValueError(f"{label} must be a string.")
    return value


def _validate_char(value: object, label: str) -> str:
    """Validate a single-character profile field."""
    text = _validate_string(value, label)
    if len(text) != 1:
        raise ValueError(f"{label} must be exactly one character.")
    return text


def _validate_colors(value: object, label: str) -> ThemeColors:
    """Validate the optional colors section for a profile."""
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object.")

    validated: dict[str, str] = {}
    for key, color_value in value.items():
        if key not in _PROFILE_COLOR_KEYS:
            raise ValueError(f"{label}.{key} is not a supported color key.")
        text = _validate_string(color_value, f"{label}.{key}")
        try:
            resolve_color_code(text)
        except ValueError as exc:
            raise ValueError(f"{label}.{key}: {exc}") from exc
        validated[key] = text

    return cast(ThemeColors, validated)


def _validate_profile(profile_name: str, profile: object, source: str) -> RenderProfile:
    """Validate one profile object and return a normalized typed mapping."""
    if not isinstance(profile, dict):
        raise ValueError(f"Profile '{profile_name}' in {source} must be an object.")

    validated: dict[str, object] = {}
    for key, value in profile.items():
        field_label = f"Profile '{profile_name}' field '{key}'"
        if key not in _PROFILE_KEYS:
            raise ValueError(f"{field_label} is not supported.")
        if key in _PROFILE_NUMERIC_KEYS:
            validated[key] = _validate_number(value, field_label)
        elif key in _PROFILE_INTEGER_KEYS:
            integer_value = _validate_int(value, field_label)
            if key in {"peak_hold_frames", "history_rows"} and integer_value < 0:
                raise ValueError(f"{field_label} must be zero or greater.")
            validated[key] = integer_value
        elif key in _PROFILE_BOOLEAN_KEYS:
            validated[key] = _validate_bool(value, field_label)
        elif key in _PROFILE_CHAR_KEYS:
            validated[key] = _validate_char(value, field_label)
        elif key == "db_marker_style":
            marker_style = _validate_string(value, field_label)
            if marker_style not in {"all", "spaced", "minimal"}:
                raise ValueError(
                    f"{field_label} must be one of: all, spaced, minimal."
                )
            validated[key] = marker_style
        elif key == "volume_mode":
            volume_mode = _validate_string(value, field_label)
            if volume_mode not in {"relative", "absolute"}:
                raise ValueError(
                    f"{field_label} must be one of: relative, absolute."
                )
            validated[key] = volume_mode
        elif key == "channel_mode":
            channel_mode = _validate_string(value, field_label)
            if channel_mode not in {"mono", "left", "right", "sum", "mid", "side"}:
                raise ValueError(
                    f"{field_label} must be one of: mono, left, right, sum, mid, side."
                )
            validated[key] = channel_mode
        elif key == "title_text":
            validated[key] = _validate_string(value, field_label)
        elif key == "history_gradient":
            history_gradient = _validate_string(value, field_label)
            if history_gradient == "":
                raise ValueError(f"{field_label} must not be empty.")
            validated[key] = history_gradient
        elif key == "colors":
            validated[key] = _validate_colors(value, field_label)

    return cast(RenderProfile, validated)


def load_profile(profile_file: str | None, profile_name: str) -> RenderProfile:
    """Load one named profile from a file or the built-in profile set."""
    if profile_file is None:
        selected = _BUILTIN_PROFILES.get(profile_name)
        if selected is None:
            available = ", ".join(list_builtin_profiles())
            raise ValueError(
                f"Unknown built-in profile: {profile_name}. Available: {available}"
            )
        return _validate_profile(profile_name, selected, "built-in profiles")

    path = Path(profile_file)
    if not path.exists():
        raise ValueError(f"Profile file does not exist: {profile_file}")

    try:
        content = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid profile JSON: {exc}") from exc

    profiles_obj = content.get("profiles") if isinstance(content, dict) else None
    if not isinstance(profiles_obj, dict):
        raise ValueError("Profile file must define a top-level 'profiles' object.")

    selected = profiles_obj.get(profile_name)
    if selected is None:
        available = ", ".join(sorted(str(name) for name in profiles_obj))
        raise ValueError(
            f"Unknown profile: {profile_name}. Available in file: {available}"
        )

    return _validate_profile(profile_name, selected, str(path))


def resolve_color_code(value: str | None) -> str | None:
    """Resolve a color name or numeric ANSI code into an ANSI escape sequence."""
    if value is None:
        return None

    raw = value.strip().lower()
    if not raw or raw == "none":
        return None

    if raw in _COLOR_MAP:
        return _COLOR_MAP[raw]

    if raw.isdigit():
        code = int(raw)
        if 30 <= code <= 37 or 90 <= code <= 97:
            return f"\x1b[{code}m"

    raise ValueError(
        "Unsupported color value. Use named colors like 'cyan' "
        "or ANSI codes 30-37/90-97."
    )
