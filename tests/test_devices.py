from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pytest

from eq_cli.audio import AudioInputDevice, AudioInputDeviceProvider
from eq_cli.cli import main


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

    def _fake_run_equalizer(device: AudioInputDevice, **kwargs: object) -> int:
        captured["device"] = device
        captured.update(kwargs)
        return 0

    monkeypatch.setattr("eq_cli.cli.run_equalizer", _fake_run_equalizer)

    exit_code = main(
        ["--device", "mic-1", "--profile", "studio"],
        device_provider=fake_provider,
    )

    assert exit_code == 0
    assert captured["peak_hold_frames"] == 12
    assert captured["volume_mode"] == "absolute"


def test_main_mode_studio_applies_preset_defaults(
    fake_provider: FakeAudioInputDeviceProvider,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Mode presets should apply default behavior for studio analysis."""
    captured: dict[str, object] = {}

    def _fake_run_equalizer(device: AudioInputDevice, **kwargs: object) -> int:
        captured["device"] = device
        captured.update(kwargs)
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

    def _fake_run_equalizer(device: AudioInputDevice, **kwargs: object) -> int:
        captured["device"] = device
        captured.update(kwargs)
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
