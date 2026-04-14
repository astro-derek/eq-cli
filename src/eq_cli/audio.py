from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class AudioInputDevice:
    """Represents a single input-capable audio device."""

    identifier: str
    name: str
    is_default: bool = False


class AudioInputDeviceProvider(ABC):
    """Abstract provider for discovering input-capable audio devices."""

    @abstractmethod
    def list_input_devices(self) -> list[AudioInputDevice]:
        """Return the currently available input devices."""


class SoundDeviceProvider(AudioInputDeviceProvider):
    """Discover audio input devices through the optional sounddevice backend."""

    def list_input_devices(self) -> list[AudioInputDevice]:
        """Query the backend and return all input-capable devices.

        Raises:
            RuntimeError: If the sounddevice dependency is unavailable.
        """
        try:
            import sounddevice  # type: ignore[import-untyped]
        except ImportError as exc:
            raise RuntimeError(
                "The sounddevice package is required for device discovery. "
                "Install it with 'pip install sounddevice'."
            ) from exc

        devices: list[AudioInputDevice] = []
        default_index = sounddevice.default.device[0]
        for index, device in enumerate(sounddevice.query_devices()):
            max_input_channels = int(device.get("max_input_channels", 0))
            if max_input_channels <= 0:
                continue

            name = str(device.get("name", f"Input Device {index}"))
            devices.append(
                AudioInputDevice(
                    identifier=str(index),
                    name=name,
                    is_default=(index == default_index),
                )
            )

        return devices
