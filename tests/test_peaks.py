from __future__ import annotations

import pytest

from eq_cli.peaks import PeakTracker
from eq_cli.renderer import RenderFrame, TerminalRenderer
from eq_cli.spectrum import DB_FLOOR, build_log_frequency_centers


def test_peak_rises_to_match_new_high_signal() -> None:
    """A peak should rise immediately when the incoming level exceeds it."""
    tracker = PeakTracker(band_count=3)

    updated = tracker.update((-10.0, -20.0, -30.0))

    assert updated[0] == pytest.approx(-10.0)
    assert updated[1] == pytest.approx(-20.0)
    assert updated[2] == pytest.approx(-30.0)


def test_peak_decays_when_signal_drops() -> None:
    """A peak should gradual decay below its current value when signal drops."""
    tracker = PeakTracker(band_count=1, decay_db_per_step=1.0)

    tracker.update((-10.0,))
    decayed = tracker.update((-80.0,))

    assert -80.0 <= decayed[0] < -10.0


def test_peak_bands_are_independent() -> None:
    """Peak decay in one band should not affect any other band."""
    tracker = PeakTracker(band_count=2, decay_db_per_step=1.0)

    tracker.update((-10.0, -10.0))
    result = tracker.update((-80.0, -10.0))

    assert result[0] < -10.0
    assert result[1] == pytest.approx(-10.0)


def test_peak_never_rises_above_ceiling_db() -> None:
    """Peak values should be capped at the +6 dB ceiling."""
    tracker = PeakTracker(band_count=1)

    result = tracker.update((10.0,))

    assert result[0] == pytest.approx(6.0)


def test_peak_hold_frames_delays_decay() -> None:
    """Configured hold frames should postpone peak decay."""
    tracker = PeakTracker(band_count=1, decay_db_per_step=1.0, hold_frames=2)

    tracker.update((-10.0,))
    held_1 = tracker.update((-80.0,))
    held_2 = tracker.update((-80.0,))
    decayed = tracker.update((-80.0,))

    assert held_1[0] == pytest.approx(-10.0)
    assert held_2[0] == pytest.approx(-10.0)
    assert decayed[0] < -10.0


def test_peak_tracker_rejects_negative_hold_frames() -> None:
    """Negative hold frame settings should be rejected."""
    with pytest.raises(ValueError, match="Hold frames"):
        PeakTracker(band_count=1, hold_frames=-1)


def test_peak_reset_clears_all_bands_to_floor() -> None:
    """Reset should immediately clear held peaks to floor."""
    tracker = PeakTracker(band_count=3, hold_frames=4)

    tracker.update((-10.0, -20.0, -30.0))
    reset_levels = tracker.reset()

    assert reset_levels == pytest.approx((DB_FLOOR, DB_FLOOR, DB_FLOOR))


def test_render_frame_with_peaks_includes_peak_markers() -> None:
    """Rendered output with peaks held above the bar should show peak markers."""
    frequencies = tuple(build_log_frequency_centers(20.0, 20_000.0, 32))
    levels = tuple([DB_FLOOR] * 32)
    peaks = tuple([-10.0] * 32)

    frame = RenderFrame(
        frequencies_hz=frequencies,
        levels_db=levels,
        peak_levels_db=peaks,
    )
    renderer = TerminalRenderer(color_enabled=False)

    output = renderer.render(frame)

    assert "-" in output
