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
    # Linear-interpolation indices and weights for sampling FFT magnitudes at
    # each band-center frequency.  These are used so narrow log bands (below
    # ~100 Hz where the log-band width is smaller than one FFT bin) still
    # receive a magnitude sample instead of dropping to the dB floor.
    center_lo_bin: npt.NDArray[np.int64]
    center_hi_bin: npt.NDArray[np.int64]
    center_hi_weight: npt.NDArray[np.float64]


def _blackman_harris_window(frame_size: int) -> npt.NDArray[np.float64]:
    """Return a 4-term Blackman-Harris window.

    Blackman-Harris has much lower spectral sidelobes (~-92 dB) than the
    Hann window (~-31 dB), which greatly reduces the visible "leakage"
    peaks that spread across higher log-frequency bands when a narrow
    tone (like a 50 Hz sine) is analyzed.
    """
    if frame_size <= 1:
        return np.ones(max(frame_size, 1), dtype=np.float64)
    indices = np.arange(frame_size, dtype=np.float64)
    denom = float(frame_size - 1)
    return (
        0.35875
        - 0.48829 * np.cos(2.0 * np.pi * indices / denom)
        + 0.14128 * np.cos(4.0 * np.pi * indices / denom)
        - 0.01168 * np.cos(6.0 * np.pi * indices / denom)
    )


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

        # Sample the FFT magnitude at each band's center frequency using
        # linear interpolation between neighboring bins.  For narrow
        # low-frequency log bands whose width is smaller than one FFT bin,
        # this yields a meaningful magnitude where a searchsorted-style
        # bin-range scan would otherwise return nothing and cause the
        # visible peak to jump to a neighboring band.
        lo_bins = frame_cache.center_lo_bin
        hi_bins = frame_cache.center_hi_bin
        hi_weights = frame_cache.center_hi_weight
        interpolated = (
            magnitudes[lo_bins] * (1.0 - hi_weights)
            + magnitudes[hi_bins] * hi_weights
        )
        band_magnitudes = interpolated.astype(np.float64, copy=True)

        # In addition, take the max across any bins that fall strictly
        # inside the band range.  This preserves behavior at high
        # frequencies where many bins land in the same log band.
        for index in range(self.band_count):
            start = int(frame_cache.band_starts[index])
            end = int(frame_cache.band_ends[index])
            if start < end:
                bin_max = float(np.max(magnitudes[start:end]))
                if bin_max > band_magnitudes[index]:
                    band_magnitudes[index] = bin_max

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

        # Pre-compute linear-interpolation indices/weights for sampling FFT
        # magnitudes at each band-center frequency.  Clamp to the valid bin
        # range so narrow bands near the edges remain well-defined.
        bin_hz = float(self.sample_rate) / float(frame_size)
        max_bin = frequencies_hz.size - 1
        if bin_hz > 0 and max_bin >= 0:
            center_float_bin = np.clip(
                self._band_centers / bin_hz,
                0.0,
                float(max_bin),
            )
        else:
            center_float_bin = np.zeros(self.band_count, dtype=np.float64)
        center_lo_bin = np.floor(center_float_bin).astype(np.int64)
        center_hi_bin = np.minimum(center_lo_bin + 1, max_bin).astype(np.int64)
        center_hi_weight = (center_float_bin - center_lo_bin).astype(np.float64)

        cache = _FrameSizeCache(
            window=_blackman_harris_window(frame_size),
            frequencies_hz=frequencies_hz,
            band_starts=band_starts,
            band_ends=band_ends,
            center_lo_bin=center_lo_bin,
            center_hi_bin=center_hi_bin,
            center_hi_weight=center_hi_weight,
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
