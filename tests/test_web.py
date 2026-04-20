"""Tests for the web server and configuration helpers."""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.request

import pytest

from eq_cli.app import get_app_version
from eq_cli.loop import RenderConfig
from eq_cli.web import WebServer, ansi_to_css, build_web_config

# ── ansi_to_css ────────────────────────────────────────────────────────────────


def test_ansi_to_css_cyan() -> None:
    """Cyan ANSI code should map to the expected CSS hex color."""
    assert ansi_to_css("\x1b[36m") == "#44cccc"


def test_ansi_to_css_red() -> None:
    """Red ANSI code should map to the expected CSS hex color."""
    assert ansi_to_css("\x1b[31m") == "#cc4444"


def test_ansi_to_css_green() -> None:
    """Green ANSI code should map to the expected CSS hex color."""
    assert ansi_to_css("\x1b[32m") == "#44cc44"


def test_ansi_to_css_bright_white() -> None:
    """Bright white (97) ANSI code should map to the expected CSS hex color."""
    assert ansi_to_css("\x1b[97m") == "#ffffff"


def test_ansi_to_css_none_returns_default() -> None:
    """None input should return the default grey color."""
    assert ansi_to_css(None) == "#aaaaaa"


def test_ansi_to_css_unrecognised_returns_default() -> None:
    """An unrecognised ANSI code should fall back to the default grey."""
    assert ansi_to_css("\x1b[99m") == "#aaaaaa"


def test_ansi_to_css_empty_string_returns_default() -> None:
    """An empty string should fall back to the default grey."""
    assert ansi_to_css("") == "#aaaaaa"


# ── build_web_config ──────────────────────────────────────────────────────────


def test_build_web_config_has_required_keys() -> None:
    """The web config dict must contain all keys consumed by the browser UI."""
    cfg = build_web_config(RenderConfig())
    required = {
        "db_min", "db_max", "db_interval", "graph_height", "band_count",
        "gain_db", "volume_mode", "channel_mode",
        "bar_color", "peak_color", "history_color", "axis_color", "label_color",
        "show_title", "show_axis_labels", "show_shortcuts",
        "db_marker_style", "history_rows", "peak_hold_frames",
        "app_version", "profile_presets",
    }
    missing = required - cfg.keys()
    assert not missing, f"Missing config keys: {missing}"


def test_build_web_config_bar_color_is_css_hex() -> None:
    """bar_color should be a CSS hex string derived from the ANSI code."""
    cfg = build_web_config(RenderConfig(bar_color_code="\x1b[36m"))
    assert cfg["bar_color"] == "#44cccc"


def test_build_web_config_peak_color_is_css_hex() -> None:
    """peak_color should be a CSS hex string derived from the ANSI code."""
    cfg = build_web_config(RenderConfig(peak_color_code="\x1b[31m"))
    assert cfg["peak_color"] == "#cc4444"


def test_build_web_config_resolves_auto_graph_height() -> None:
    """graph_height=0 should be resolved to a positive integer."""
    cfg = build_web_config(
        RenderConfig(db_min=-80, db_max=6, db_interval=10, graph_height=0)
    )
    assert cfg["graph_height"] > 0


def test_build_web_config_preserves_explicit_graph_height() -> None:
    """An explicit non-zero graph_height must be preserved unchanged."""
    cfg = build_web_config(RenderConfig(graph_height=20))
    assert cfg["graph_height"] == 20


def test_build_web_config_excludes_title_text() -> None:
    """Web config should not expose title text as a user setting."""
    cfg = build_web_config(RenderConfig())
    assert "title_text" not in cfg


def test_build_web_config_passthrough_scalars() -> None:
    """Scalar display fields should be forwarded unchanged."""
    cfg = build_web_config(
        RenderConfig(
            db_min=-60.0,
            db_max=0.0,
            db_interval=6.0,
            gain_db=3.0,
            history_rows=4,
            peak_hold_frames=8,
        )
    )
    assert cfg["db_min"] == -60.0
    assert cfg["db_max"] == 0.0
    assert cfg["db_interval"] == 6.0
    assert cfg["gain_db"] == 3.0
    assert cfg["history_rows"] == 4
    assert cfg["peak_hold_frames"] == 8


def test_build_web_config_axis_frequencies_none_by_default() -> None:
    """axis_frequencies should be None when not configured."""
    cfg = build_web_config(RenderConfig())
    assert cfg["axis_frequencies"] is None


def test_build_web_config_axis_frequencies_serialised() -> None:
    """axis_frequencies should be serialised to a list when configured."""
    cfg = build_web_config(
        RenderConfig(axis_frequencies=(100.0, 1000.0, 10000.0))
    )
    assert cfg["axis_frequencies"] == [100.0, 1000.0, 10000.0]


def test_build_web_config_exposes_profile_presets() -> None:
    """Built-in profile presets should be exported for the web settings panel."""
    cfg = build_web_config(RenderConfig())
    presets = cfg["profile_presets"]
    assert isinstance(presets, dict)
    assert {
        "studio",
        "default",
        "green-based",
        "minimal",
        "neon-night",
        "sunset-drive",
    } <= set(presets)
    assert "bar_color" in presets["studio"]
    assert "peak_color" in presets["studio"]


def test_build_web_config_includes_app_version() -> None:
    """The app version exposed to the browser should be a non-empty string."""
    cfg = build_web_config(RenderConfig())
    assert isinstance(cfg["app_version"], str)
    assert cfg["app_version"] != ""


# ── WebServer lifecycle ───────────────────────────────────────────────────────


def test_web_server_port_zero_gets_os_assigned_port() -> None:
    """Binding to port 0 should result in an OS-assigned non-zero port."""
    server = WebServer("127.0.0.1", 0, build_web_config(RenderConfig()))
    server.start()
    try:
        assert server.port > 0
    finally:
        server.stop()


def test_web_server_url_reflects_bound_port() -> None:
    """The url property should embed the actual bound port."""
    server = WebServer("127.0.0.1", 0, build_web_config(RenderConfig()))
    server.start()
    try:
        assert server.url.startswith("http://127.0.0.1:")
        assert str(server.port) in server.url
    finally:
        server.stop()


def test_web_server_serves_config_json() -> None:
    """The /config endpoint should return a JSON object with db_min."""
    config_data = build_web_config(RenderConfig())
    server = WebServer("127.0.0.1", 0, config_data)
    server.start()
    try:
        with urllib.request.urlopen(f"{server.url}config") as resp:
            data = json.loads(resp.read())
        assert data["db_min"] == -80.0
        assert "bar_color" in data
    finally:
        server.stop()


def test_web_server_config_content_type_is_json() -> None:
    """The /config endpoint Content-Type header should be application/json."""
    server = WebServer("127.0.0.1", 0, build_web_config(RenderConfig()))
    server.start()
    try:
        with urllib.request.urlopen(f"{server.url}config") as resp:
            assert "application/json" in resp.headers.get("Content-Type", "")
    finally:
        server.stop()


def test_web_server_serves_index_html() -> None:
    """The root endpoint should serve the HTML page with a canvas element."""
    server = WebServer("127.0.0.1", 0, build_web_config(RenderConfig()))
    server.start()
    try:
        with urllib.request.urlopen(f"{server.url}") as resp:
            html = resp.read().decode()
        assert "<canvas" in html
        assert "<title>frequency-analyzer</title>" in html
        assert '<link rel="icon" type="image/svg+xml" href="/favicon.svg">' in html
        assert 'id="version-badge"' in html
        assert 'id="repo-link"' in html
        assert 'id="tb-meta"' in html
        assert 'id="sel-profile"' in html
        assert '<label for="device-select">Device:</label>' in html
        assert '<label for="device-select">&#127908;</label>' not in html
        assert 'id="cfg-volume_mode"' in html
        assert 'id="cfg-channel_mode"' in html
        assert 'id="cfg-fft_size"' in html
        assert 'id="cfg-graph_style"' in html
        assert 'id="cfg-history_fps"' in html
        assert 'id="cfg-history_rows" step="1" min="0" inputmode="numeric"' in html
        assert 'id="cfg-history_fps" step="1" min="1" inputmode="numeric"' in html
        assert 'id="cfg-gain_db" step="0.5" inputmode="decimal"' in html
        assert 'id="cfg-title_text"' not in html
        assert "CFG.title_text" not in html
        assert "<u>F</u>reeze" in html
        assert "<u>R</u>eset Peaks" in html
        assert "<u>S</u>napshot" in html
        assert (
            'id="btn-freeze" title="[F] Freeze display" '
            'accesskey="f" aria-keyshortcuts="f"'
        ) in html
        assert (
            'id="btn-reset" title="[R] Reset peaks" '
            'accesskey="r" aria-keyshortcuts="r"'
        ) in html
        assert (
            'id="btn-snap" title="[S] Save PNG" '
            'accesskey="s" aria-keyshortcuts="s"'
        ) in html
        assert "[F] Freeze:" not in html
        assert "document.title = 'frequency-analyzer';" in html
        assert "var runtimeStatusMessage = 'No device selected';" in html
        assert "function setRuntimeStatusMessage(msg) {" in html
        assert "runtimeStatusMessage = msg;" in html
        assert (
            r"var titleStr = 'frequency-analyzer \u2014 ' + runtimeStatusMessage;"
            in html
        )
        assert "setRuntimeStatusMessage('Analyzing\\u2026');" in html
        assert "setRuntimeStatusMessage('Stopped');" in html
        assert "if (isFrozen) { titleStr += ' \\u25ae FROZEN'; }" in html
        assert "function drawPeakDbLabels(peaks)" in html
        assert "drawPeakDbLabels(peaks);" in html
        # Hover tooltip is a browser-only setting exposed via the Settings
        # panel; verify the checkbox, default CFG value, and draw path exist.
        assert 'id="cfg-show_hover_tooltip"' in html
        assert "show_hover_tooltip: false" in html
        assert "function drawHoverTooltip()" in html
        assert "drawHoverTooltip();" in html
        meta_match = re.search(
            r'<div class="tb-group" id="tb-meta">(?P<section>.*?)</div>',
            html,
            flags=re.DOTALL,
        )
        assert meta_match is not None
        meta_section = meta_match.group("section")
        assert 'id="repo-link"' in meta_section
        assert 'id="version-badge"' in meta_section
        assert meta_section.index('id="repo-link"') < meta_section.index(
            'id="version-badge"'
        )
    finally:
        server.stop()


def test_web_server_injects_default_version_in_index() -> None:
    """Served index HTML should include the resolved fallback app version."""
    server = WebServer("127.0.0.1", 0, build_web_config(RenderConfig()))
    server.start()
    try:
        with urllib.request.urlopen(f"{server.url}") as resp:
            html = resp.read().decode()
        assert f"var DEFAULT_VERSION = '{get_app_version()}';" in html
        assert "__EQ_CLI_VERSION__" not in html
    finally:
        server.stop()


def test_web_index_defers_boot_until_dom_ready() -> None:
    """The page should defer UI wiring/init until DOMContentLoaded fires."""
    server = WebServer("127.0.0.1", 0, build_web_config(RenderConfig()))
    server.start()
    try:
        with urllib.request.urlopen(f"{server.url}") as resp:
            html = resp.read().decode()
        assert "function wireUi()" in html
        listener = "window.addEventListener('DOMContentLoaded', function () {"
        listener_idx = html.find(listener)
        assert listener_idx != -1, "DOMContentLoaded listener was not found"
        wire_idx = html.find("wireUi();", listener_idx)
        assert wire_idx != -1, "wireUi() was not called in DOMContentLoaded listener"
        init_idx = html.find("init();", wire_idx)
        assert init_idx != -1, "init() was not called after wireUi()"
        assert listener_idx < wire_idx < init_idx
        assert len(re.findall(r"\bwireUi\(\);", html)) == 1
        assert len(re.findall(r"\binit\(\);", html)) == 1
    finally:
        server.stop()


def test_web_index_places_freeze_controls_in_footer() -> None:
    """Freeze/Reset/Snapshot controls should render in the footer, not toolbar."""
    server = WebServer("127.0.0.1", 0, build_web_config(RenderConfig()))
    server.start()
    try:
        with urllib.request.urlopen(f"{server.url}") as resp:
            html = resp.read().decode()

        toolbar_idx = html.find('<div id="toolbar">')
        canvas_idx = html.find('<div id="canvas-container">')
        footer_idx = html.find('<div id="footer">')
        script_idx = html.find("<script>")

        assert toolbar_idx != -1
        assert canvas_idx != -1
        assert footer_idx != -1
        assert script_idx != -1
        assert toolbar_idx < canvas_idx < footer_idx < script_idx

        toolbar_section = html[toolbar_idx:canvas_idx]
        assert 'id="btn-freeze"' not in toolbar_section
        assert 'id="btn-reset"' not in toolbar_section
        assert 'id="btn-snap"' not in toolbar_section

        footer_section = html[footer_idx:script_idx]
        assert 'id="btn-freeze"' in footer_section
        assert 'id="btn-reset"' in footer_section
        assert 'id="btn-snap"' in footer_section
    finally:
        server.stop()


def test_web_index_does_not_persist_server_managed_profile_fields() -> None:
    """Browser-saved settings must not overwrite server-managed profile presets."""
    server = WebServer("127.0.0.1", 0, build_web_config(RenderConfig()))
    server.start()
    try:
        with urllib.request.urlopen(f"{server.url}") as resp:
            html = resp.read().decode()
        assert "function _persistableSettings(source)" in html
        assert "delete settings.profile_presets;" in html
        assert "delete settings.app_version;" in html
    finally:
        server.stop()


def test_web_index_positions_db_labels_from_db_values() -> None:
    """dB labels should be positioned from their dB values, not row centers."""
    server = WebServer("127.0.0.1", 0, build_web_config(RenderConfig()))
    server.start()
    try:
        with urllib.request.urlopen(f"{server.url}") as resp:
            html = resp.read().decode()
        assert "var y = dbToY(Number(dbLabelRows[ri]));" in html
        assert "var y = barY + Number(ri) * L.rowH + L.rowH / 2;" not in html
    finally:
        server.stop()


def test_web_index_embeds_fallback_profile_presets() -> None:
    """Static page should include fallback built-in profile presets."""
    server = WebServer("127.0.0.1", 0, build_web_config(RenderConfig()))
    server.start()
    try:
        with urllib.request.urlopen(f"{server.url}", timeout=5) as resp:
            html = resp.read().decode()
        assert "var DEFAULT_PROFILE_PRESETS = {" in html
        assert "'default': {" in html
        assert "'green-based': {" in html
        assert "'high-contrast': {" in html
        assert "'minimal': {" in html
        assert "'neon-night': {" in html
        assert "'studio': {" in html
        assert "'sunset-drive': {" in html

        # default profile
        assert "bar_color: '#44cccc'" in html
        assert "peak_color: '#cc4444'" in html
        assert "history_color: '#44cccc'" in html
        assert "axis_color: '#666666'" in html
        assert "label_color: '#aaaaaa'" in html

        # green-based profile
        assert "bar_color: '#44cc44'" in html
        assert "peak_color: '#66ff66'" in html
        assert "history_color: '#66ff66'" in html
        assert "axis_color: '#66ff66'" in html
        assert "label_color: '#44cc44'" in html

        # high-contrast profile
        assert "bar_color: '#66ffff'" in html
        assert "peak_color: '#ff6666'" in html
        assert "history_color: '#66ffff'" in html
        assert "axis_color: '#ffffff'" in html
        assert "label_color: '#ffff66'" in html

        # minimal profile
        assert "bar_color: '#aaaaaa'" in html
        assert "peak_color: '#ffffff'" in html
        assert "history_color: '#aaaaaa'" in html
        assert "axis_color: '#666666'" in html
        assert "label_color: '#aaaaaa'" in html

        # studio profile
        assert "bar_color: '#44cc44'" in html
        assert "peak_color: '#ff6666'" in html
        assert "history_color: '#44cc44'" in html
        assert "axis_color: '#777777'" in html
        assert "label_color: '#ffffff'" in html

        # neon-night profile
        assert "bar_color: '#66ffff'" in html
        assert "peak_color: '#ffff66'" in html
        assert "history_color: '#ff66ff'" in html
        assert "axis_color: '#6666ff'" in html
        assert "label_color: '#ff66ff'" in html

        # sunset-drive profile
        assert "bar_color: '#ff66ff'" in html
        assert "peak_color: '#ff6666'" in html
        assert "history_color: '#66ffff'" in html
        assert "axis_color: '#777777'" in html
        assert "label_color: '#ffff66'" in html
    finally:
        server.stop()


def test_web_index_frequency_axis_alignment_and_label_anchor() -> None:
    """Frequency-axis line and labels should align with the y-axis origin."""
    server = WebServer("127.0.0.1", 0, build_web_config(RenderConfig()))
    server.start()
    try:
        with urllib.request.urlopen(f"{server.url}") as resp:
            html = resp.read().decode()
        assert "ctx.fillRect(barX - 1, freqAxY, barW + 1, 1);" in html
        assert "ctx.textAlign = 'left';" in html
    finally:
        server.stop()


def test_web_index_maps_frequency_markers_to_band_positions() -> None:
    """Frequency markers should be placed from rendered band centers."""
    server = WebServer("127.0.0.1", 0, build_web_config(RenderConfig()))
    server.start()
    try:
        with urllib.request.urlopen(f"{server.url}") as resp:
            html = resp.read().decode()
        assert "function frequencyToBandPosition(freq) {" in html
        assert "if (freq <= BAND_CENTERS[0]) { return 0; }" in html
        assert "if (freq >= BAND_CENTERS[count - 1]) { return count - 1; }" in html
        assert "var lo = BAND_CENTERS[i];" in html
        assert "var hi = BAND_CENTERS[i + 1];" in html
        assert "var denom = Math.log(hi) - Math.log(lo);" in html
        assert "var t = (Math.log(freq) - Math.log(lo)) / denom;" in html
        assert "return i + Math.max(0, Math.min(1, t));" in html
        assert (
            "var minF = BAND_EDGES[0], maxF = BAND_EDGES[BAND_EDGES.length - 1];"
            in html
        )
        assert "var pos = frequencyToBandPosition(freq);" in html
        assert "var x = L.barX + Math.round(((pos + 0.5) / count) * L.barW);" in html
    finally:
        server.stop()


def test_web_index_includes_graph_style_setting() -> None:
    """Settings and renderer should support both filled bars and line graph modes."""
    server = WebServer("127.0.0.1", 0, build_web_config(RenderConfig()))
    server.start()
    try:
        with urllib.request.urlopen(f"{server.url}") as resp:
            html = resp.read().decode()
        assert '<label for="cfg-graph_style">Graph style</label>' in html
        assert '<option value="filled">Filled bars</option>' in html
        assert '<option value="line">Line graph</option>' in html
        assert "if ((CFG.graph_style || 'filled') === 'line') {" in html
    finally:
        server.stop()


def test_web_band_span_uses_consistent_width_step() -> None:
    """Band spans should use one width step for all bars across the graph."""
    server = WebServer("127.0.0.1", 0, build_web_config(RenderConfig()))
    server.start()
    try:
        with urllib.request.urlopen(f"{server.url}") as resp:
            html = resp.read().decode()
        assert "if (count <= 0) { return; }" in html
        assert "var step = W / count;" in html
        assert "bandSpans.push({ x: L.barX + i * step, w: Math.max(1, step) });" in html
        assert "var x0 = Math.round(i * W / count);" not in html
    finally:
        server.stop()


def test_web_fft_bin_mapping_uses_center_interpolation() -> None:
    """FFT bin-to-band mapping should interpolate at each band center.

    The interpolation guarantees every band (including narrow low-frequency
    log bands where width < one FFT bin) receives a magnitude sample, which
    fixes 50 Hz tones showing leakage peaks beyond 100 Hz on the log axis.
    """
    server = WebServer("127.0.0.1", 0, build_web_config(RenderConfig()))
    server.start()
    try:
        with urllib.request.urlopen(f"{server.url}") as resp:
            html = resp.read().decode()
        # Center-frequency interpolation must happen in computeBandLevels
        assert "var centerBin = BAND_CENTERS[b] / binHz;" in html
        assert "var frac = centerBin - k0;" in html
        assert "var mx = v0 * (1 - frac) + v1 * frac;" in html
        # And we still scan any bins strictly inside the band
        assert "var lo = Math.max(0, Math.ceil(BAND_EDGES[b] / binHz));" in html
        assert (
            "var hi = Math.min(fftData.length, Math.ceil(BAND_EDGES[b + 1] / binHz));"
            in html
        )
    finally:
        server.stop()


def test_web_server_serves_index_html_via_explicit_path() -> None:
    """Accessing /index.html explicitly should also serve the page."""
    server = WebServer("127.0.0.1", 0, build_web_config(RenderConfig()))
    server.start()
    try:
        with urllib.request.urlopen(f"{server.url}index.html") as resp:
            html = resp.read().decode()
        assert "<canvas" in html
    finally:
        server.stop()


def test_web_server_serves_favicon_svg() -> None:
    """The favicon asset should be served from the static directory."""
    server = WebServer("127.0.0.1", 0, build_web_config(RenderConfig()))
    server.start()
    try:
        with urllib.request.urlopen(f"{server.url}favicon.svg") as resp:
            content = resp.read().decode()
            content_type = resp.headers.get("Content-Type", "")
        assert "<svg" in content
        assert "image/svg+xml" in content_type
    finally:
        server.stop()


def test_web_server_returns_404_for_unknown_path() -> None:
    """Requesting an unknown path should produce a 404 response."""
    server = WebServer("127.0.0.1", 0, build_web_config(RenderConfig()))
    server.start()
    try:
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(f"{server.url}nonexistent")
        assert exc_info.value.code == 404
    finally:
        server.stop()


def test_web_server_stop_is_idempotent() -> None:
    """Calling stop() after the server has already stopped must not raise."""
    server = WebServer("127.0.0.1", 0, build_web_config(RenderConfig()))
    server.start()
    server.stop()
    server.stop()  # second call should be silent


def test_web_server_config_reflects_custom_render_config() -> None:
    """Custom RenderConfig values must be visible in the served /config JSON."""
    custom = RenderConfig(
        db_min=-60.0,
        db_max=0.0,
        volume_mode="absolute",
        show_title=False,
    )
    server = WebServer("127.0.0.1", 0, build_web_config(custom))
    server.start()
    try:
        with urllib.request.urlopen(f"{server.url}config") as resp:
            data = json.loads(resp.read())
        assert data["db_min"] == -60.0
        assert data["db_max"] == 0.0
        assert data["volume_mode"] == "absolute"
        assert data["show_title"] is False
    finally:
        server.stop()
