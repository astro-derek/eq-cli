"""Web-mode entry point for the equalizer.

Audio capture and real-time FFT processing run entirely inside the browser via
the Web Audio API.  Python serves a static single-page application together
with a ``/config`` endpoint that supplies display parameters derived from the
active CLI profile.  No ``sounddevice`` dependency is required for this mode.
"""
from __future__ import annotations

import sys
import time
import webbrowser

from eq_cli.loop import RenderConfig
from eq_cli.web import WebServer, build_web_config


def run_equalizer_web(
    config: RenderConfig | None = None,
    web_host: str = "127.0.0.1",
    web_port: int = 8080,
    open_browser: bool = False,
) -> int:
    """Start the web-mode equalizer.

    Starts a local HTTP server that serves the browser-based spectrum
    analyzer UI.  Audio capture and FFT processing happen entirely inside the
    browser, so no audio device needs to be selected before calling this
    function.

    Args:
        config: Display and rendering parameters derived from the active CLI
            profile.  Defaults to ``RenderConfig()`` when not provided.
        web_host: Interface address to bind the HTTP server to.  Defaults to
            ``"127.0.0.1"`` (loopback only, single-user local access).
        web_port: TCP port for the HTTP server.
        open_browser: Open the system default browser automatically on startup.

    Returns:
        Process exit code: ``0`` for a clean exit, ``1`` on server error.
    """
    effective_config = config if config is not None else RenderConfig()
    config_data = build_web_config(effective_config)
    server = WebServer(
        host=web_host,
        port=web_port,
        config_data=config_data,
    )
    try:
        server.start()
    except OSError as exc:
        sys.stderr.write(
            f"Cannot start web server on {web_host}:{web_port}: {exc}\n"
        )
        return 1

    print(f"eq-cli web UI: {server.url}")
    print(
        "Audio capture runs entirely in the browser — "
        "select an input device from the in-page dropdown."
    )
    print("Press Ctrl+C to stop the server.")

    if open_browser:
        webbrowser.open(server.url)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        server.stop()

    return 0
