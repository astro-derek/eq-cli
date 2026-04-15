from __future__ import annotations

from collections import OrderedDict
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
_FRAME_CACHE_MAX_SIZE = 8


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


@dataclass(frozen=True)
class _FrameSizeCache:
    """Cached FFT metadata for a specific frame size."""

    window: npt.NDArray[np.float64]
    frequencies_hz: npt.NDArray[np.float64]
    band_starts: npt.NDArray[np.int64]
    band_ends: npt.NDArray[np.int64]


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
        self._band_centers_tuple = tuple(float(value) for value in self._band_centers)
        self._band_edges = build_log_frequency_edges(
            min_frequency_hz,
            max_frequency_hz,
            band_count,
        )
        self._smooth_peak: float = 1e-10
        self._peak_decay: float = 0.90
        self._frame_size_cache: OrderedDict[int, _FrameSizeCache] = OrderedDict()

    def process_frame(self, frame: AudioFrame) -> SpectrumBands:
        """Convert one audio frame into display-ready log-spaced band levels."""
        if frame.sample_rate != self.sample_rate:
            raise ValueError("Frame sample rate does not match processor sample rate.")
        if frame.samples.size == 0:
            raise ValueError("Audio frame must contain at least one sample.")

        frame_cache = self._frame_cache(frame.samples.size)
        windowed = frame.samples * frame_cache.window
        spectrum = np.fft.rfft(windowed)
        magnitudes = np.abs(spectrum)
        band_magnitudes = np.zeros(self.band_count, dtype=np.float64)

        for index in range(self.band_count):
            start = int(frame_cache.band_starts[index])
            end = int(frame_cache.band_ends[index])
            if start < end:
                band_magnitudes[index] = float(np.max(magnitudes[start:end]))

        levels_db = self._levels_to_db(band_magnitudes, frame.samples.size)

        return SpectrumBands(
            frequencies_hz=self._band_centers_tuple,
            levels_db=tuple(float(value) for value in levels_db),
        )

    def _frame_cache(self, frame_size: int) -> _FrameSizeCache:
        """Return cached FFT metadata for the requested frame size."""
        cache = self._frame_size_cache.get(frame_size)
        if cache is not None:
            return cache

        frequencies_hz = np.fft.rfftfreq(
            frame_size,
            d=1.0 / float(self.sample_rate),
        ).astype(np.float64)
        band_starts = np.searchsorted(
            frequencies_hz,
            self._band_edges[:-1],
            side="left",
        ).astype(np.int64)
        band_ends = np.searchsorted(
            frequencies_hz,
            self._band_edges[1:],
            side="left",
        ).astype(np.int64)
        band_ends[-1] = np.searchsorted(
            frequencies_hz,
            self._band_edges[-1],
            side="right",
        )

        cache = _FrameSizeCache(
            window=np.hanning(frame_size),
            frequencies_hz=frequencies_hz,
            band_starts=band_starts,
            band_ends=band_ends,
        )
        if len(self._frame_size_cache) >= _FRAME_CACHE_MAX_SIZE:
            self._frame_size_cache.popitem(last=False)
        self._frame_size_cache[frame_size] = cache
        return cache

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
