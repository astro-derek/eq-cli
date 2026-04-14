from __future__ import annotations

from eq_cli.spectrum import DB_FLOOR

DEFAULT_DECAY_DB_PER_STEP = 0.5
MAX_DB = 6.0


class PeakTracker:
    """Track per-band peak levels with gradual decay."""

    def __init__(
        self,
        band_count: int,
        decay_db_per_step: float = DEFAULT_DECAY_DB_PER_STEP,
        hold_frames: int = 0,
        max_db: float = MAX_DB,
        floor_db: float = DB_FLOOR,
    ) -> None:
        """Initialize the tracker with zeroed peak state."""
        if band_count <= 0:
            raise ValueError("Band count must be greater than zero.")
        if hold_frames < 0:
            raise ValueError("Hold frames must be zero or greater.")
        self._decay = decay_db_per_step
        self._hold_frames = hold_frames
        self._max_db = max_db
        self._floor_db = floor_db
        self._peaks: list[float] = [floor_db] * band_count
        self._hold_counts: list[int] = [0] * band_count

    def update(self, levels_db: tuple[float, ...]) -> tuple[float, ...]:
        """Return peak levels after merging new signal levels with current state."""
        for index, level in enumerate(levels_db):
            clamped = min(level, self._max_db)
            if clamped >= self._peaks[index]:
                self._peaks[index] = clamped
                self._hold_counts[index] = self._hold_frames
            elif self._hold_counts[index] > 0:
                self._hold_counts[index] -= 1
            else:
                self._peaks[index] = max(
                    self._floor_db,
                    self._peaks[index] - self._decay,
                )

        return tuple(self._peaks)

    def reset(self) -> tuple[float, ...]:
        """Reset all tracked peaks back to floor and clear hold counters."""
        self._peaks = [self._floor_db] * len(self._peaks)
        self._hold_counts = [0] * len(self._hold_counts)
        return tuple(self._peaks)
