from __future__ import annotations

import dataclasses
import json
from dataclasses import dataclass
from pathlib import Path

import pytest

from eq_cli.audio import AudioInputDevice, AudioInputDeviceProvider
from eq_cli.cli import main
from eq_cli.loop import RenderConfig


@dataclass
class FakeAudioInputDeviceProvider(AudioInputDeviceProvider):
    """Test double for deterministic audio device discovery."""

    devices: list[AudioInputDevice]

    def list_input_devices(self) -> list[AudioInputDevice]:
        """Return the configured fake devices."""
        return list(self.devices)


@pytest.fixture
def fake_provider() -> FakeAudioInputDeviceProvider:
    """Provide a repeatable set of fake audio devices for CLI tests."""
    return FakeAudioInputDeviceProvider(
        devices=[
            AudioInputDevice(identifier="mic-1", name="Desk Mic", is_default=True),
            AudioInputDevice(identifier="mic-2", name="USB Mic"),
        ]
    )


def test_main_lists_devices(
    fake_provider: FakeAudioInputDeviceProvider,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The CLI should list available input devices and exit successfully."""
    exit_code = main(["--list-devices"], device_provider=fake_provider)

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "mic-1" in captured.out
    assert "Desk Mic" in captured.out
    assert "mic-2" in captured.out
    assert "(default)" in captured.out
    assert "USB Mic * (default)" not in captured.out


def test_main_selects_device_from_argument(
    fake_provider: FakeAudioInputDeviceProvider,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The CLI should accept a device identifier passed by argument."""
    exit_code = main(
        ["--device", "mic-2"],
        device_provider=fake_provider,
        loop_func=lambda _device: 0,
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Selected input device: USB Mic (mic-2)" in captured.out


def test_main_prompts_for_device_selection(
    fake_provider: FakeAudioInputDeviceProvider,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The CLI should prompt for a device when none is provided."""
    exit_code = main(
        [],
        device_provider=fake_provider,
        input_func=lambda _prompt: "2",
        loop_func=lambda _device: 0,
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Select an input device" in captured.out
    assert "Selected input device: USB Mic (mic-2)" in captured.out


def test_main_returns_error_for_unknown_device(
    fake_provider: FakeAudioInputDeviceProvider,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The CLI should fail cleanly when the requested device does not exist."""
    exit_code = main(["--device", "missing"], device_provider=fake_provider)

    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Unknown input device: missing" in captured.err


def test_main_returns_error_when_no_input_devices_exist(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The CLI should fail cleanly when no input devices are available."""
    provider = FakeAudioInputDeviceProvider(devices=[])

    exit_code = main([], device_provider=provider)

    captured = capsys.readouterr()

    assert exit_code == 1
    assert "No audio input devices are available." in captured.err


def test_main_loads_named_profile_file(
    fake_provider: FakeAudioInputDeviceProvider,
    tmp_path: Path,
) -> None:
    """CLI should accept a valid profile file and profile name."""
    profile_file = tmp_path / "profiles.json"
    profile_file.write_text(
        json.dumps(
            {
                "profiles": {
                    "studio": {
                        "axis_labels": True,
                        "db_marker_style": "minimal",
                        "colors": {"bar": "cyan", "peak": "red"},
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    exit_code = main(
        [
            "--device",
            "mic-1",
            "--profile-file",
            str(profile_file),
            "--profile",
            "studio",
        ],
        device_provider=fake_provider,
        loop_func=lambda _device: 0,
    )

    assert exit_code == 0


def test_main_returns_error_for_invalid_profile_file(
    fake_provider: FakeAudioInputDeviceProvider,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """CLI should fail cleanly when requested profile file is missing."""
    exit_code = main(
        [
            "--device",
            "mic-1",
            "--profile-file",
            "missing-profiles.json",
            "--profile",
            "studio",
        ],
        device_provider=fake_provider,
    )

    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Profile file does not exist" in captured.err


def test_main_loads_builtin_profile_without_profile_file(
    fake_provider: FakeAudioInputDeviceProvider,
) -> None:
    """CLI should allow built-in profiles without requiring a profile file."""
    exit_code = main(
        ["--device", "mic-1", "--profile", "studio"],
        device_provider=fake_provider,
        loop_func=lambda _device: 0,
    )

    assert exit_code == 0


def test_main_lists_built_in_profiles(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """CLI should print built-in profile names and exit."""
    exit_code = main(["--list-profiles"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "default" in captured.out
    assert "studio" in captured.out


def test_main_applies_peak_hold_frames_from_profile(
    fake_provider: FakeAudioInputDeviceProvider,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Built-in profile peak hold should be applied before loop start."""
    captured: dict[str, object] = {}

    def _fake_run_equalizer(
        device: AudioInputDevice, config: RenderConfig | None = None
    ) -> int:
        captured["device"] = device
        captured.update(dataclasses.asdict(config) if config is not None else {})
        return 0

    monkeypatch.setattr("eq_cli.cli.run_equalizer", _fake_run_equalizer)

    exit_code = main(
        ["--device", "mic-1", "--profile", "studio"],
        device_provider=fake_provider,
    )

    assert exit_code == 0
    assert captured["peak_hold_frames"] == 12
    assert captured["volume_mode"] == "absolute"
    assert captured["history_rows"] == 0
    assert captured["db_min"] == -76.0
    assert captured["db_max"] == 0.0
    assert captured["graph_height"] == 24
    assert captured["graph_width"] == 140
    assert captured["peak_char"] == "_"
    assert captured["snapshot_format"] == "ansi"
    assert captured["snapshot_dir"] == "snapshots"


def test_main_applies_peak_db_labels_from_profile(
    fake_provider: FakeAudioInputDeviceProvider,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Profile peak dB label defaults should reach the render loop."""
    captured: dict[str, object] = {}
    profile_file = tmp_path / "profiles.json"
    profile_file.write_text(
        json.dumps(
            {
                "profiles": {
                    "analysis": {
                        "peak_db_labels": True,
                        "snapshot_format": "ansi",
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    def _fake_run_equalizer(
        device: AudioInputDevice, config: RenderConfig | None = None
    ) -> int:
        captured["device"] = device
        captured.update(dataclasses.asdict(config) if config is not None else {})
        return 0

    monkeypatch.setattr("eq_cli.cli.run_equalizer", _fake_run_equalizer)

    exit_code = main(
        [
            "--device",
            "mic-1",
            "--profile-file",
            str(profile_file),
            "--profile",
            "analysis",
        ],
        device_provider=fake_provider,
    )

    assert exit_code == 0
    assert captured["peak_db_labels"] is True
    assert captured["snapshot_format"] == "ansi"


def test_main_passes_exportable_profile_to_loop(
    fake_provider: FakeAudioInputDeviceProvider,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CLI should pass the effective exportable profile configuration to the loop."""
    captured: dict[str, object] = {}

    def _fake_run_equalizer(
        device: AudioInputDevice, config: RenderConfig | None = None
    ) -> int:
        captured["device"] = device
        captured.update(dataclasses.asdict(config) if config is not None else {})
        return 0

    monkeypatch.setattr("eq_cli.cli.run_equalizer", _fake_run_equalizer)

    exit_code = main(
        [
            "--device",
            "mic-1",
            "--profile",
            "studio",
            "--gain",
            "3.5",
            "--refresh-rate",
            "45",
            "--block-size",
            "2048",
            "--axis-frequencies",
            "50,100,1000,5000",
            "--peak-db-labels",
            "--color-bar",
            "bright_green",
            "--snapshot-file",
            "captures/current.txt",
        ],
        device_provider=fake_provider,
    )

    export_profile = captured["export_profile"]

    assert exit_code == 0
    assert isinstance(export_profile, dict)
    assert export_profile["gain"] == 3.5
    assert export_profile["graph_height"] == 24
    assert export_profile["refresh_rate"] == 45.0
    assert export_profile["block_size"] == 2048
    assert export_profile["axis_frequencies"] == (50.0, 100.0, 1000.0, 5000.0)
    assert export_profile["peak_db_labels"] is True
    assert export_profile["snapshot_format"] == "ansi"
    assert export_profile["snapshot_file"] == "captures/current.txt"
    assert export_profile["colors"]["bar"] == "bright_green"


def test_main_applies_extended_runtime_settings_from_profile(
    fake_provider: FakeAudioInputDeviceProvider,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Profiles should be able to set runtime tuning values beyond render style."""
    captured: dict[str, object] = {}
    profile_file = tmp_path / "profiles.json"
    profile_file.write_text(
        json.dumps(
            {
                "profiles": {
                    "analysis": {
                        "gain": 4.5,
                        "refresh_rate": 50.0,
                        "block_size": 1024,
                        "axis_frequencies": [50.0, 100.0, 1000.0],
                        "snapshot_file": "captures/startup.txt",
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    def _fake_run_equalizer(
        device: AudioInputDevice, config: RenderConfig | None = None
    ) -> int:
        captured["device"] = device
        captured.update(dataclasses.asdict(config) if config is not None else {})
        return 0

    monkeypatch.setattr("eq_cli.cli.run_equalizer", _fake_run_equalizer)

    exit_code = main(
        [
            "--device",
            "mic-1",
            "--profile-file",
            str(profile_file),
            "--profile",
            "analysis",
        ],
        device_provider=fake_provider,
    )

    assert exit_code == 0
    assert captured["gain_db"] == 4.5
    assert captured["refresh_rate"] == 50.0
    assert captured["block_size"] == 1024
    assert captured["axis_frequencies"] == (50.0, 100.0, 1000.0)
    assert captured["snapshot_file"] == "captures/startup.txt"


def test_main_passes_explicit_graph_height_to_loop(
    fake_provider: FakeAudioInputDeviceProvider,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CLI should forward explicit graph height to the render loop."""
    captured: dict[str, object] = {}

    def _fake_run_equalizer(
        device: AudioInputDevice, config: RenderConfig | None = None
    ) -> int:
        captured["device"] = device
        captured.update(dataclasses.asdict(config) if config is not None else {})
        return 0

    monkeypatch.setattr("eq_cli.cli.run_equalizer", _fake_run_equalizer)

    exit_code = main(
        ["--device", "mic-1", "--graph-height", "14"],
        device_provider=fake_provider,
    )

    assert exit_code == 0
    assert captured["graph_height"] == 14


def test_main_passes_axis_frequencies_and_block_size_to_loop(
    fake_provider: FakeAudioInputDeviceProvider,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CLI should forward custom axis labels and block size to the loop."""
    captured: dict[str, object] = {}

    def _fake_run_equalizer(
        device: AudioInputDevice, config: RenderConfig | None = None
    ) -> int:
        captured["device"] = device
        captured.update(dataclasses.asdict(config) if config is not None else {})
        return 0

    monkeypatch.setattr("eq_cli.cli.run_equalizer", _fake_run_equalizer)

    exit_code = main(
        [
            "--device",
            "mic-1",
            "--axis-frequencies",
            "50,100,1000,5000",
            "--block-size",
            "2048",
        ],
        device_provider=fake_provider,
    )

    assert exit_code == 0
    assert captured["axis_frequencies"] == (50.0, 100.0, 1000.0, 5000.0)
    assert captured["block_size"] == 2048


def test_main_passes_snapshot_settings_to_loop(
    fake_provider: FakeAudioInputDeviceProvider,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CLI should forward snapshot configuration to the render loop."""
    captured: dict[str, object] = {}

    def _fake_run_equalizer(
        device: AudioInputDevice, config: RenderConfig | None = None
    ) -> int:
        captured["device"] = device
        captured.update(dataclasses.asdict(config) if config is not None else {})
        return 0

    monkeypatch.setattr("eq_cli.cli.run_equalizer", _fake_run_equalizer)

    exit_code = main(
        [
            "--device",
            "mic-1",
            "--snapshot-file",
            "snapshots/frame.txt",
            "--snapshot-format",
            "ansi",
            "--snapshot-dir",
            "snapshots",
        ],
        device_provider=fake_provider,
    )

    assert exit_code == 0
    assert captured["snapshot_file"] == "snapshots/frame.txt"
    assert captured["snapshot_format"] == "ansi"
    assert captured["snapshot_dir"] == "snapshots"


def test_main_mode_studio_applies_preset_defaults(
    fake_provider: FakeAudioInputDeviceProvider,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Mode presets should apply default behavior for studio analysis."""
    captured: dict[str, object] = {}

    def _fake_run_equalizer(
        device: AudioInputDevice, config: RenderConfig | None = None
    ) -> int:
        captured["device"] = device
        captured.update(dataclasses.asdict(config) if config is not None else {})
        return 0

    monkeypatch.setattr("eq_cli.cli.run_equalizer", _fake_run_equalizer)

    exit_code = main(
        ["--device", "mic-1", "--mode", "studio"],
        device_provider=fake_provider,
    )

    assert exit_code == 0
    assert captured["volume_mode"] == "absolute"
    assert captured["peak_hold_frames"] == 12
    assert captured["title_text"] == "eq-cli studio"
    assert captured["channel_mode"] == "sum"


def test_main_mode_allows_explicit_cli_overrides(
    fake_provider: FakeAudioInputDeviceProvider,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Explicit CLI flags should override mode preset defaults."""
    captured: dict[str, object] = {}

    def _fake_run_equalizer(
        device: AudioInputDevice, config: RenderConfig | None = None
    ) -> int:
        captured["device"] = device
        captured.update(dataclasses.asdict(config) if config is not None else {})
        return 0

    monkeypatch.setattr("eq_cli.cli.run_equalizer", _fake_run_equalizer)

    exit_code = main(
        [
            "--device",
            "mic-1",
            "--mode",
            "studio",
            "--volume-mode",
            "relative",
            "--channel-mode",
            "left",
        ],
        device_provider=fake_provider,
    )

    assert exit_code == 0
    assert captured["volume_mode"] == "relative"
    assert captured["channel_mode"] == "left"


def test_main_web_mode_uses_frequency_analyzer_title_by_default(
    fake_provider: FakeAudioInputDeviceProvider,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Web mode should default the chart/page title to frequency-analyzer."""
    captured: dict[str, object] = {}

    def _fake_run_equalizer_web(
        config: RenderConfig,
        web_host: str,
        web_port: int,
        open_browser: bool,
    ) -> int:
        captured["title_text"] = config.title_text
        captured["web_host"] = web_host
        captured["web_port"] = web_port
        captured["open_browser"] = open_browser
        return 0

    monkeypatch.setattr("eq_cli.web_loop.run_equalizer_web", _fake_run_equalizer_web)

    exit_code = main(["--ui", "web"], device_provider=fake_provider)

    assert exit_code == 0
    assert captured["title_text"] == "frequency-analyzer"
