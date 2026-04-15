from __future__ import annotations

import time

import numpy as np

from eq_cli.spectrum import (
    DB_FLOOR,
    AudioFrame,
    SpectrumProcessor,
    build_log_frequency_centers,
    magnitude_to_db,
)


def _build_sine_samples(
    sample_rate: int,
    frame_size: int,
    frequency_hz: float,
    amplitude: float = 1.0,
) -> np.ndarray:
    """Build a deterministic sine wave frame for spectrum tests."""
    time_axis = np.arange(frame_size) / sample_rate
    return amplitude * np.sin(2.0 * np.pi * frequency_hz * time_axis)


def test_build_log_frequency_centers_returns_expected_range() -> None:
    """The band centers should cover 20 Hz to 20 kHz with 32 log-spaced bins."""
    centers = build_log_frequency_centers(20.0, 20_000.0, 32)

    assert len(centers) == 32
    assert centers[0] >= 20.0
    assert centers[-1] <= 20_000.0
    assert np.all(np.diff(centers) > 0)


def test_magnitude_to_db_is_monotonic_and_floors_silence() -> None:
    """dB conversion should floor silence and increase with larger magnitudes."""
    values = magnitude_to_db(np.array([0.0, 0.01, 0.1, 1.0]))

    assert values[0] == DB_FLOOR
    assert values[1] < values[2] < values[3]
    assert values[-1] == 0.0


def test_spectrum_processor_emits_32_band_levels_for_sine_wave() -> None:
    """The processor should emit 32 dB levels and matching centers for each frame."""
    sample_rate = 48_000
    frame_size = 2_048
    time_axis = np.arange(frame_size) / sample_rate
    samples = np.sin(2.0 * np.pi * 1_000.0 * time_axis)

    processor = SpectrumProcessor(sample_rate=sample_rate, band_count=32)
    result = processor.process_frame(
        AudioFrame(samples=samples, sample_rate=sample_rate)
    )

    assert len(result.frequencies_hz) == 32
    assert len(result.levels_db) == 32
    assert max(result.levels_db) <= 0.0
    assert min(result.levels_db) >= DB_FLOOR


def test_spectrum_processor_default_band_count_is_64() -> None:
    """The default band count should be 64."""
    sample_rate = 48_000
    frame_size = 4_096
    samples = np.zeros(frame_size)

    processor = SpectrumProcessor(sample_rate=sample_rate)
    result = processor.process_frame(
        AudioFrame(samples=samples, sample_rate=sample_rate)
    )

    assert len(result.frequencies_hz) == 64
    assert len(result.levels_db) == 64


def test_log_centers_include_bins_between_10k_and_20k() -> None:
    """Band centers should include multiple bins in the 10 kHz to 20 kHz range."""
    centers = build_log_frequency_centers(20.0, 20_000.0, 64)

    high_band = centers[(centers > 10_000.0) & (centers < 20_000.0)]
    assert high_band.size >= 2


def test_spectrum_processor_levels_bounded_by_zero_db() -> None:
    """With EMA normalisation, no band should exceed 0 dB."""
    sample_rate = 48_000
    frame_size = 2_048
    samples = np.ones(frame_size)

    processor = SpectrumProcessor(sample_rate=sample_rate, band_count=32)
    result = processor.process_frame(
        AudioFrame(samples=samples, sample_rate=sample_rate)
    )

    assert all(level <= 0.0 for level in result.levels_db)


def test_relative_mode_carves_out_dynamic_range() -> None:
    """Relative mode should normalize the strongest band near 0 dB."""
    sample_rate = 48_000
    frame_size = 2_048
    time_axis = np.arange(frame_size) / sample_rate
    samples = 0.05 * np.sin(2.0 * np.pi * 1_000.0 * time_axis)

    processor = SpectrumProcessor(
        sample_rate=sample_rate,
        band_count=32,
        volume_mode="relative",
    )
    result = processor.process_frame(
        AudioFrame(samples=samples, sample_rate=sample_rate)
    )

    assert max(result.levels_db) > -1.0


def test_absolute_mode_preserves_true_level() -> None:
    """Absolute mode should keep low-amplitude signals below 0 dB."""
    sample_rate = 48_000
    frame_size = 2_048
    time_axis = np.arange(frame_size) / sample_rate
    samples = 0.05 * np.sin(2.0 * np.pi * 1_000.0 * time_axis)

    processor = SpectrumProcessor(
        sample_rate=sample_rate,
        band_count=32,
        volume_mode="absolute",
    )
    result = processor.process_frame(
        AudioFrame(samples=samples, sample_rate=sample_rate)
    )

    assert max(result.levels_db) < -5.0


def test_absolute_mode_registers_high_frequency_tones() -> None:
    """Absolute mode should still register strong tones above 10 kHz."""
    sample_rate = 48_000
    frame_size = 4_096
    time_axis = np.arange(frame_size) / sample_rate
    samples = 0.5 * np.sin(2.0 * np.pi * 16_000.0 * time_axis)

    processor = SpectrumProcessor(
        sample_rate=sample_rate,
        band_count=64,
        volume_mode="absolute",
    )
    result = processor.process_frame(
        AudioFrame(samples=samples, sample_rate=sample_rate)
    )

    peak_index = max(
        range(len(result.levels_db)),
        key=lambda index: result.levels_db[index],
    )

    assert result.levels_db[peak_index] > -20.0
    assert result.frequencies_hz[peak_index] > 10_000.0


def test_spectrum_processor_is_stable_for_repeated_same_size_frames() -> None:
    """Repeated absolute-mode processing should be stable for the same frame size."""
    sample_rate = 48_000
    samples = _build_sine_samples(sample_rate, 2_048, 1_000.0, amplitude=0.25)
    frame = AudioFrame(samples=samples, sample_rate=sample_rate)
    processor = SpectrumProcessor(
        sample_rate=sample_rate,
        band_count=64,
        volume_mode="absolute",
    )

    first = processor.process_frame(frame)
    second = processor.process_frame(frame)

    assert first.frequencies_hz == second.frequencies_hz
    assert np.allclose(first.levels_db, second.levels_db)


def test_spectrum_processor_handles_frame_size_changes_without_drift() -> None:
    """Changing frame size between calls should not corrupt cached DSP state."""
    sample_rate = 48_000
    processor = SpectrumProcessor(
        sample_rate=sample_rate,
        band_count=64,
        volume_mode="absolute",
    )

    small_frame = AudioFrame(
        samples=_build_sine_samples(sample_rate, 2_048, 1_000.0, amplitude=0.25),
        sample_rate=sample_rate,
    )
    large_frame = AudioFrame(
        samples=_build_sine_samples(sample_rate, 4_096, 1_000.0, amplitude=0.25),
        sample_rate=sample_rate,
    )

    small_before = processor.process_frame(small_frame)
    large_result = processor.process_frame(large_frame)
    small_after = processor.process_frame(small_frame)

    small_peak_before = max(
        range(len(small_before.levels_db)),
        key=small_before.levels_db.__getitem__,
    )
    large_peak = max(
        range(len(large_result.levels_db)),
        key=large_result.levels_db.__getitem__,
    )
    small_peak_after = max(
        range(len(small_after.levels_db)),
        key=small_after.levels_db.__getitem__,
    )

    assert small_before.frequencies_hz[small_peak_before] > 900.0
    assert large_result.frequencies_hz[large_peak] > 900.0
    assert small_after.frequencies_hz[small_peak_after] > 900.0
    assert np.allclose(small_before.levels_db, small_after.levels_db)


def test_spectrum_processor_meets_minimum_throughput_target() -> None:
    """Processing synthetic frames should exceed the baseline 20 FPS target."""
    sample_rate = 48_000
    frame_size = 2_048
    time_axis = np.arange(frame_size) / sample_rate
    samples = np.sin(2.0 * np.pi * 440.0 * time_axis)
    frame = AudioFrame(samples=samples, sample_rate=sample_rate)
    processor = SpectrumProcessor(sample_rate=sample_rate, band_count=32)

    start = time.perf_counter()
    for _ in range(100):
        processor.process_frame(frame)
    duration = time.perf_counter() - start

    assert duration < 5.0


# ---------------------------------------------------------------------------
# m2: dead functions removed
# ---------------------------------------------------------------------------


def test_apply_window_no_longer_exported() -> None:
    """apply_window should have been removed as it was dead code."""
    import eq_cli.spectrum as spectrum_module

    assert not hasattr(spectrum_module, "apply_window"), (
        "apply_window was dead code and should have been removed"
    )


def test_compute_fft_magnitude_no_longer_exported() -> None:
    """compute_fft_magnitude should have been removed as it was dead code."""
    import eq_cli.spectrum as spectrum_module

    assert not hasattr(spectrum_module, "compute_fft_magnitude"), (
        "compute_fft_magnitude was dead code and should have been removed"
    )
