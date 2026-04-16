"""Local HTTP server for the web-mode equalizer UI.

Serves a static single-page application together with a ``/config`` endpoint
that supplies display parameters derived from the active CLI profile.  Audio
capture and real-time FFT processing run entirely inside the browser via the
Web Audio API; Python provides only the page and display configuration.
"""
from __future__ import annotations

import http.server
import json
import math
import re
import threading
from pathlib import Path
from typing import Any

from eq_cli.app import get_app_version
from eq_cli.loop import RenderConfig
from eq_cli.profile import list_builtin_profiles, load_profile, resolve_color_code

_STATIC_DIR = Path(__file__).parent / "static"
_VERSION_PLACEHOLDER = "__EQ_CLI_VERSION__"
_LEGACY_VERSION_LINE = "var DEFAULT_VERSION = '0.0.0';"

_ANSI_CODE_TO_CSS: dict[str, str] = {
    "30": "#555555",
    "31": "#cc4444",
    "32": "#44cc44",
    "33": "#cccc44",
    "34": "#4444cc",
    "35": "#cc44cc",
    "36": "#44cccc",
    "37": "#aaaaaa",
    "90": "#777777",
    "91": "#ff6666",
    "92": "#66ff66",
    "93": "#ffff66",
    "94": "#6666ff",
    "95": "#ff66ff",
    "96": "#66ffff",
    "97": "#ffffff",
}

_DEFAULT_CSS_COLOR = "#aaaaaa"


def ansi_to_css(ansi_code: str | None) -> str:
    """Convert an ANSI escape sequence to a CSS hex color string.

    Args:
        ansi_code: An ANSI escape sequence such as ``\\x1b[36m``, or ``None``.

    Returns:
        A CSS hex color string.  Unrecognised or ``None`` inputs fall back to
        ``"#aaaaaa"``.
    """
    if ansi_code is None:
        return _DEFAULT_CSS_COLOR
    match = re.match(r"\x1b\[(\d+)m", ansi_code)
    if match:
        return _ANSI_CODE_TO_CSS.get(match.group(1), _DEFAULT_CSS_COLOR)
    return _DEFAULT_CSS_COLOR


def _resolve_graph_height(
    graph_height: int,
    db_min: float,
    db_max: float,
    db_interval: float,
) -> int:
    """Return the effective graph height, computing from the dB scale when zero.

    Mirrors the logic in ``renderer._default_graph_height`` so the browser
    receives the same resolved row count as the terminal renderer.

    Args:
        graph_height: Configured height; ``0`` means derive from the dB scale.
        db_min: Bottom of the dB display range.
        db_max: Top of the dB display range.
        db_interval: Row spacing in dB.

    Returns:
        Resolved positive integer graph height.
    """
    if graph_height > 0:
        return graph_height
    top = math.floor(db_max / db_interval) * db_interval
    row_count = 0
    current = top
    while current >= db_min - 1e-9:
        row_count += 1
        current = round(current - db_interval, 10)
    if row_count == 0 or abs(top - db_max) > 1e-9:
        row_count += 1
    return max(1, row_count)


def _profile_color_to_css(color_name: str | None) -> str | None:
    """Resolve a profile color name to a CSS hex color string.

    Args:
        color_name: Optional profile color name accepted by
            ``resolve_color_code``.

    Returns:
        The resolved CSS hex color string, or ``None`` when no color name is
        provided or the profile color resolves to ``None``.
    """
    if color_name is None:
        return None
    ansi_code = resolve_color_code(color_name)
    if ansi_code is None:
        return None
    return ansi_to_css(ansi_code)


def _build_web_profile_presets() -> dict[str, dict[str, str]]:
    """Build built-in profile presets consumable by the web settings UI.

    Returns:
        A mapping keyed by built-in profile name.  Each value is a mapping of
        web config color keys (``bar_color``, ``peak_color``,
        ``history_color``, ``axis_color``, ``label_color``) to CSS hex color
        strings.
    """
    presets: dict[str, dict[str, str]] = {}
    for profile_name in list_builtin_profiles():
        profile = load_profile(None, profile_name)
        colors = profile.get("colors")
        if not isinstance(colors, dict):
            continue

        bar_color = _profile_color_to_css(colors.get("bar"))
        peak_color = _profile_color_to_css(colors.get("peak"))
        history_color = _profile_color_to_css(colors.get("history")) or bar_color
        axis_color = _profile_color_to_css(colors.get("axis"))
        label_color = _profile_color_to_css(colors.get("label"))

        preset: dict[str, str] = {}
        if bar_color is not None:
            preset["bar_color"] = bar_color
        if peak_color is not None:
            preset["peak_color"] = peak_color
        if history_color is not None:
            preset["history_color"] = history_color
        if axis_color is not None:
            preset["axis_color"] = axis_color
        if label_color is not None:
            preset["label_color"] = label_color

        if preset:
            presets[profile_name] = preset
    return presets


def build_web_config(config: RenderConfig) -> dict[str, Any]:
    """Build a JSON-serialisable display configuration dict for the web UI.

    Translates ANSI color codes to CSS hex strings and resolves the automatic
    graph height so the browser receives fully resolved values ready for
    canvas rendering.

    Args:
        config: The resolved render configuration to expose to the browser.

    Returns:
        A flat dictionary safe for ``json.dumps`` and serving at ``/config``.
    """
    graph_height = _resolve_graph_height(
        config.graph_height,
        config.db_min,
        config.db_max,
        config.db_interval,
    )
    return {
        "db_min": config.db_min,
        "db_max": config.db_max,
        "db_interval": config.db_interval,
        "graph_height": graph_height,
        "band_count": 128,
        "gain_db": config.gain_db,
        "volume_mode": config.volume_mode,
        "channel_mode": config.channel_mode,
        "bar_color": ansi_to_css(config.bar_color_code),
        "peak_color": ansi_to_css(config.peak_color_code),
        "history_color": ansi_to_css(
            config.history_color_code or config.bar_color_code
        ),
        "axis_color": ansi_to_css(config.axis_color_code),
        "label_color": ansi_to_css(config.label_color_code),
        "show_title": config.show_title,
        "title_text": config.title_text or "frequency-analyzer",
        "show_axis_labels": config.show_axis_labels,
        "show_shortcuts": config.show_shortcuts,
        "db_marker_style": config.db_marker_style,
        "history_rows": config.history_rows,
        "history_gradient": config.history_gradient,
        "peak_hold_frames": config.peak_hold_frames,
        "peak_db_labels": config.peak_db_labels,
        "axis_frequencies": (
            list(config.axis_frequencies) if config.axis_frequencies else None
        ),
        "band_gap": config.band_gap,
        "app_version": get_app_version(),
        "profile_presets": _build_web_profile_presets(),
    }


def _make_handler_class(
    config_data: dict[str, Any],
) -> type[http.server.BaseHTTPRequestHandler]:
    """Return a request handler class closed over the given configuration data.

    Args:
        config_data: JSON-serialisable display configuration to serve at
            ``/config``.

    Returns:
        A ``BaseHTTPRequestHandler`` subclass bound to the provided data.
    """

    class _Handler(http.server.BaseHTTPRequestHandler):
        def log_message(
            self,
            fmt: str,
            *args: object,
        ) -> None:
            """Suppress HTTP access log output."""

        def do_GET(self) -> None:
            """Dispatch GET requests to the page or config endpoints."""
            if self.path in {"/", "/index.html"}:
                self._serve_file("index.html", "text/html; charset=utf-8")
            elif self.path == "/config":
                self._send_json(config_data)
            else:
                self.send_error(404)

        def _serve_file(self, filename: str, content_type: str) -> None:
            """Read and send a static file from the package static directory."""
            file_path = _STATIC_DIR / filename
            if not file_path.exists():
                self.send_error(404)
                return
            content = file_path.read_bytes()
            if filename == "index.html":
                version = get_app_version()
                placeholder = _VERSION_PLACEHOLDER.encode()
                if placeholder in content:
                    content = content.replace(placeholder, version.encode())
                else:
                    content = content.replace(
                        _LEGACY_VERSION_LINE.encode(),
                        f"var DEFAULT_VERSION = '{version}';".encode(),
                    )
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)

        def _send_json(self, data: dict[str, Any], status: int = 200) -> None:
            """Serialise and write a JSON HTTP response."""
            body = json.dumps(data).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return _Handler


class WebServer:
    """Local HTTP server for the web-mode equalizer UI.

    Serves the static ``index.html`` page and a ``/config`` endpoint that
    returns display parameters derived from the active render profile.  The
    server runs in a daemon background thread so the calling thread can block
    on ``Ctrl+C`` and cleanly stop the server via ``stop()``.
    """

    def __init__(
        self,
        host: str,
        port: int,
        config_data: dict[str, Any],
    ) -> None:
        """Create the server; call ``start()`` to begin serving requests.

        Args:
            host: Interface address to bind (e.g. ``"127.0.0.1"``).
            port: TCP port to listen on.  Pass ``0`` to let the OS assign a
                free port and read the actual port back via ``self.port``.
            config_data: Display configuration dictionary served at
                ``/config``.
        """
        self._host = host
        handler_class = _make_handler_class(config_data)
        self._server = http.server.ThreadingHTTPServer(
            (host, port), handler_class
        )
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        """Start the HTTP server in a daemon background thread."""
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            daemon=True,
            name="eq-cli-web-server",
        )
        self._thread.start()

    def stop(self) -> None:
        """Shut down the HTTP server and wait for the background thread to exit."""
        self._server.shutdown()
        if self._thread is not None:
            self._thread.join(timeout=5.0)

    @property
    def port(self) -> int:
        """Return the TCP port the server is actually bound to."""
        return int(self._server.server_address[1])

    @property
    def url(self) -> str:
        """Return the base URL of the running server."""
        return f"http://{self._host}:{self.port}/"
