# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- `_show_db_marker`: `"spaced"` style now shows dB labels only on
  interval-aligned rows instead of on every row like `"all"` (m1).
- Removed dead `apply_window` and `compute_fft_magnitude` functions from
  `spectrum.py` (m2).
- `_find_peak_row` and `_find_peak_row_index` now use `bisect` for O(log n)
  lookups instead of a linear scan (m3).
- `_save_profile_export` now uses exclusive file creation (`open(..., "x")`)
  to atomically claim a numbered slot, eliminating the TOCTOU race in
  `_next_profile_export_path` (m4).
- `_frame_size_cache` in `SpectrumProcessor` and `_layout_cache` in
  `TerminalRenderer` are now capped at 8 entries with FIFO eviction (m10).

### Added
- `CHANGELOG.md` (this file).
- `SECURITY.md` with responsible-disclosure contact.
- `pytest-cov` as an optional `dev` dependency; coverage can be collected
  with `pytest --cov=eq_cli` after `pip install -e .[dev]`.

## [0.1.1] — 2026-04-14

### Fixed
- Exported profiles no longer include `"block_size": null` when `--block-size`
  was not set, preventing a `ValueError` on re-import (C2).
- `--db-interval 0` and `"db_interval": 0` in profile files are now rejected
  with a clear error instead of raising `ZeroDivisionError` (C3).
- `--db-min` equal to or greater than `--db-max` is now rejected with a clear
  cross-parameter validation error (M3).
- Release workflow now runs `pytest`, `ruff`, and `mypy` before building
  distribution artifacts, preventing broken releases (M7).
- `softprops/action-gh-release` is pinned to a commit SHA instead of a mutable
  tag, eliminating a supply-chain risk (M8).
- `import sounddevice` is now deferred to the point of use inside
  `run_equalizer()`, preventing `OSError: PortAudio library not found` at
  import time on machines without the native PortAudio library (C1).

### Changed
- `run_equalizer` now accepts a frozen `RenderConfig` dataclass instead of
  33 individual keyword arguments (M4).
- `_merge_profile_settings` now uses type-grouped module-level tables for all
  profile field merging instead of 25+ copy-paste if-blocks (M5).

## [0.1.0] — 2026-04-10

### Added
- Real-time terminal equalizer with configurable audio input device selection.
- 64 log-spaced frequency bands from 20 Hz to 20 kHz.
- Peak markers with configurable hold and decay.
- Theme/profile system with five built-in presets and support for custom JSON
  profile files.
- Centered title row with version string.
- Optional frequency and dB axis labels.
- Configurable dB marker density (`all`, `spaced`, `minimal`).
- Spectrum history display with configurable depth and character gradient.
- Runtime keyboard shortcuts: freeze (`F`), reset peaks (`R`), snapshot (`S`),
  export profile (`P`), quit (`Q`).
- Chart snapshot export in `txt` and `ansi` formats.
- Profile export to numbered JSON files.
- `relative` and `absolute` volume modes.
- CI workflow with `pytest`, `ruff`, `mypy`, and distribution artifact build.
- Release workflow that publishes `.tar.gz` and `.whl` on version tags.

[Unreleased]: https://github.com/astro-derek/eq-cli/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/astro-derek/eq-cli/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/astro-derek/eq-cli/releases/tag/v0.1.0
