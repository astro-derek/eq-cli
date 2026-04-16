"""Tests for the web-mode CLI arguments."""
from __future__ import annotations

import pytest

from eq_cli.cli import build_parser


def test_parser_default_ui_is_terminal() -> None:
    """The default value for --ui should be 'terminal'."""
    parser = build_parser()
    args = parser.parse_args([])
    assert args.ui == "terminal"


def test_parser_accepts_ui_terminal_explicitly() -> None:
    """Passing --ui terminal should set ui to 'terminal'."""
    parser = build_parser()
    args = parser.parse_args(["--ui", "terminal"])
    assert args.ui == "terminal"


def test_parser_accepts_ui_web() -> None:
    """Passing --ui web should set ui to 'web'."""
    parser = build_parser()
    args = parser.parse_args(["--ui", "web"])
    assert args.ui == "web"


def test_parser_rejects_invalid_ui_mode() -> None:
    """An unrecognised --ui value should cause the parser to exit."""
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["--ui", "curses"])


def test_parser_default_web_host() -> None:
    """The default --web-host should be '127.0.0.1'."""
    parser = build_parser()
    args = parser.parse_args([])
    assert args.web_host == "127.0.0.1"


def test_parser_accepts_web_host() -> None:
    """Custom --web-host value should be stored on the namespace."""
    parser = build_parser()
    args = parser.parse_args(["--web-host", "0.0.0.0"])
    assert args.web_host == "0.0.0.0"


def test_parser_default_web_port() -> None:
    """The default --web-port should be 8080."""
    parser = build_parser()
    args = parser.parse_args([])
    assert args.web_port == 8080


def test_parser_accepts_web_port() -> None:
    """Custom --web-port value should be parsed as an integer."""
    parser = build_parser()
    args = parser.parse_args(["--web-port", "9000"])
    assert args.web_port == 9000


def test_parser_open_browser_defaults_false() -> None:
    """The default value of --open-browser should be False."""
    parser = build_parser()
    args = parser.parse_args([])
    assert args.open_browser is False


def test_parser_accepts_open_browser_flag() -> None:
    """Passing --open-browser should set open_browser to True."""
    parser = build_parser()
    args = parser.parse_args(["--open-browser"])
    assert args.open_browser is True


def test_web_options_coexist_with_other_flags() -> None:
    """Web options must be combinable with existing display options."""
    parser = build_parser()
    args = parser.parse_args(
        [
            "--ui", "web",
            "--web-port", "9001",
            "--web-host", "localhost",
            "--open-browser",
            "--profile", "studio",
            "--db-min", "-60",
        ]
    )
    assert args.ui == "web"
    assert args.web_port == 9001
    assert args.web_host == "localhost"
    assert args.open_browser is True
    assert args.profile == "studio"
    assert args.db_min == -60.0
