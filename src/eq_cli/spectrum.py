from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import numpy.typing as npt

DB_FLOOR = -80.0
DB_CEILING = 6.0
MIN_FREQUENCY_HZ = 20.0
MAX_FREQUENCY_HZ = 20_000.0
DEFAULT_BAND_COUNT = 64
DEFAULT_VOLUME_MODE: Literal["relative", "absolute"] = "relative"


@dataclass(frozen=True)
class AudioFrame:
    """A single block of audio samples and its sampling rate."""

    samples: npt.NDArray[np.float64]
    sample_rate: int


@dataclass(frozen=True)
class SpectrumBands:
    """Log-spaced spectrum levels prepared for rendering."""

    frequencies_hz: tuple[float, ...]
    levels_db: tuple[float, ...]


def build_log_frequency_centers(
    min_frequency_hz: float,
    max_frequency_hz: float,
    band_count: int,
) -> npt.NDArray[np.float64]:
    """Return monotonically increasing log-spaced band centers."""
    if min_frequency_hz <= 0:
        raise ValueError("Minimum frequency must be greater than zero.")
    if max_frequency_hz <= min_frequency_hz:
        raise ValueError("Maximum frequency must be greater than minimum frequency.")
    if band_count <= 0:
        raise ValueError("Band count must be greater than zero.")

    return np.geomspace(
        min_frequency_hz,
        max_frequency_hz,
        band_count,
        dtype=np.float64,
    )


def build_log_frequency_edges(
    min_frequency_hz: float,
    max_frequency_hz: float,
    band_count: int,
) -> npt.NDArray[np.float64]:
    """Return log-spaced band edges used for spectrum aggregation."""
    return np.geomspace(
        min_frequency_hz,
        max_frequency_hz,
        band_count + 1,
        dtype=np.float64,
    )


def apply_window(samples: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
    """Apply a Hann window to reduce FFT spectral leakage."""
    return samples * np.hanning(samples.size)


def compute_fft_magnitude(
    samples: npt.NDArray[np.float64],
    sample_rate: int,
) -> tuple[npt.NDArray[np.float64], npt.NDArray[np.float64]]:
    """Convert a frame of samples into FFT bin frequencies and magnitudes."""
    windowed = apply_window(samples)
    spectrum = np.fft.rfft(windowed)
    frequencies = np.fft.rfftfreq(samples.size, d=1.0 / float(sample_rate))
    magnitudes = np.abs(spectrum)
    return frequencies.astype(np.float64), magnitudes.astype(np.float64)


def magnitude_to_db(values: npt.ArrayLike) -> npt.NDArray[np.float64]:
    """Convert linear magnitudes to dB with a fixed floor for silence."""
    magnitudes = np.asarray(values, dtype=np.float64)
    floor_magnitude = 10 ** (DB_FLOOR / 20.0)
    safe_magnitudes = np.maximum(magnitudes, floor_magnitude)
    levels_db = 20.0 * np.log10(safe_magnitudes)
    return np.maximum(levels_db, DB_FLOOR)


class SpectrumProcessor:
    """Process audio frames into fixed log-spaced spectrum bands."""

    def __init__(
        self,
        sample_rate: int,
        band_count: int = DEFAULT_BAND_COUNT,
        min_frequency_hz: float = MIN_FREQUENCY_HZ,
        max_frequency_hz: float = MAX_FREQUENCY_HZ,
        volume_mode: Literal["relative", "absolute"] = DEFAULT_VOLUME_MODE,
    ) -> None:
        """Initialize the processor for a fixed sampling rate and band layout."""
        self.sample_rate = sample_rate
        self.band_count = band_count
        self.min_frequency_hz = min_frequency_hz
        self.max_frequency_hz = max_frequency_hz
        self.volume_mode = volume_mode
        self._band_centers = build_log_frequency_centers(
            min_frequency_hz,
            max_frequency_hz,
            band_count,
        )
        self._band_edges = build_log_frequency_edges(
            min_frequency_hz,
            max_frequency_hz,
            band_count,
        )
        self._smooth_peak: float = 1e-10
        self._peak_decay: float = 0.90

    def process_frame(self, frame: AudioFrame) -> SpectrumBands:
        """Convert one audio frame into display-ready log-spaced band levels."""
        if frame.sample_rate != self.sample_rate:
            raise ValueError("Frame sample rate does not match processor sample rate.")
        if frame.samples.size == 0:
            raise ValueError("Audio frame must contain at least one sample.")

        frequencies, magnitudes = compute_fft_magnitude(
            frame.samples,
            frame.sample_rate,
        )
        band_magnitudes = np.zeros(self.band_count, dtype=np.float64)

        for index in range(self.band_count):
            low = self._band_edges[index]
            high = self._band_edges[index + 1]
            if index == self.band_count - 1:
                mask = (frequencies >= low) & (frequencies <= high)
            else:
                mask = (frequencies >= low) & (frequencies < high)

            if np.any(mask):
                band_magnitudes[index] = float(np.max(magnitudes[mask]))

        levels_db = self._levels_to_db(band_magnitudes, frame.samples.size)

        return SpectrumBands(
            frequencies_hz=tuple(float(value) for value in self._band_centers),
            levels_db=tuple(float(value) for value in levels_db),
        )

    def _levels_to_db(
        self,
        band_magnitudes: npt.NDArray[np.float64],
        frame_size: int,
    ) -> npt.NDArray[np.float64]:
        """Convert band magnitudes to dB according to the configured volume mode."""
        if self.volume_mode == "absolute":
            reference = max(frame_size / 4.0, 1e-10)
            return magnitude_to_db(band_magnitudes / reference)

        current_peak = float(np.max(band_magnitudes))
        if current_peak > self._smooth_peak:
            self._smooth_peak = current_peak
        else:
            self._smooth_peak = max(self._smooth_peak * self._peak_decay, 1e-10)
        return magnitude_to_db(band_magnitudes / self._smooth_peak)
