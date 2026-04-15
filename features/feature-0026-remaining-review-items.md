# Feature 0026: Remaining Code Review Items

## Status
Completed

## Objective
Address the six code review items that were explicitly deferred in feature-0025.
These span a visual bug, dead code removal, an algorithm improvement, a
concurrency correctness fix, documentation additions, and a resource-safety
improvement.

## Scope

### m1 — `'all'` vs `'spaced'` db marker styles are identical
`_show_db_marker` in `renderer.py` treats `"all"` and `"spaced"` identically
(both return `True` for every row).  The intended semantics are:

| Style     | Rows that show a dB label |
|-----------|---------------------------|
| `all`     | Every graph row           |
| `spaced`  | Only rows that coincide with a dB-interval marker (`_db_marker_labels`) |
| `minimal` | First, last, and midpoint of the marker rows |

Currently `"spaced"` shows a label on every row (wrong), making it
indistinguishable from `"all"`.

**Fix:** Change the `"all"` / `"spaced"` branch: `"all"` continues to return
`True`; `"spaced"` returns `row_index in self._db_marker_labels`.

### m2 — Dead code in `spectrum.py`
`apply_window(samples)` and `compute_fft_magnitude(samples, sample_rate)` are
standalone module-level functions that are never called by `SpectrumProcessor`
or any other production code.  `SpectrumProcessor.process_frame` performs its
own windowing and FFT inline using cached arrays.  The two functions are not
part of the public API (`__init__.py` does not export them) and have no direct
tests.

**Fix:** Remove `apply_window` and `compute_fft_magnitude`.

### m3 — O(n) linear scan in `_find_peak_row` / `_find_peak_row_index`
`_find_peak_row` iterates every row threshold to find the lowest threshold ≥
peak_db.  `_find_peak_row_index` then calls `list.index()` (another O(n) scan)
to find the result's position.  Both are called once per band per rendered
frame, so the cost scales as O(bands × rows).

**Fix:** Store the row thresholds in ascending order (`_row_thresholds_asc`) at
construction time and use `bisect.bisect_left` to find the insertion point in
O(log n).  Keep `_row_thresholds` for all other uses (row iteration is
descending).

### m4 — TOCTOU race in `_next_profile_export_path`
`_next_profile_export_path` checks `candidate.exists()` and returns the path;
`_save_profile_export` then calls `write_text`.  Between the existence check
and the write, another process (or a second concurrent hotkey press) could
create the same file, silently overwriting it.

**Fix:** Remove the separate `_next_profile_export_path` helper.  In
`_save_profile_export`, attempt to open each candidate with exclusive-create
mode (`open(candidate, "x", encoding="utf-8")`); if `FileExistsError` is
raised, advance the index and retry.  The kernel-level `O_EXCL` flag makes the
create-or-fail atomic.

### m7 — Missing `CHANGELOG.md`, `SECURITY.md`, and pytest-cov
Standard open-source project files are absent:

- `CHANGELOG.md`: Tracks release history so users know what changed.
- `SECURITY.md`: Describes how to report vulnerabilities.
- `pytest-cov`: Coverage reporting reveals untested paths and is expected by
  most CI pipelines.

**Fix:**
- Add `CHANGELOG.md` starting from `v0.1.0` with entries for `v0.1.0` and `v0.1.1`.
- Add `SECURITY.md` with a responsible-disclosure contact.
- Add `pytest-cov` to `[project.optional-dependencies]` in `pyproject.toml`
  and add `--cov=eq_cli` to the default `addopts` under a separate
  `[tool.pytest.ini_options]` section so coverage is opt-in by presence of
  the package.

### m10 — Unbounded caches in `SpectrumProcessor` and `TerminalRenderer`
`SpectrumProcessor._frame_size_cache` and `TerminalRenderer._layout_cache` are
plain `dict` objects with no eviction policy.  In normal use only one entry is
ever created (one fixed block size, one fixed graph geometry), but unusual use
of the public API (or future programmatic use) could grow the caches without
bound.

**Fix:** Cap each cache at 8 entries.  When a new entry would exceed the limit,
evict the oldest entry (FIFO) by converting the dicts to
`collections.OrderedDict` and popping the first key when full.

## Out of Scope
- Broader performance profiling or algorithmic changes beyond the targeted fixes.
- Adding new features or changing any externally visible behaviour.

## Dependencies
- Feature 0025 (must be merged; this feature builds on the same codebase).

## Acceptance Criteria
- `TerminalRenderer` with `db_marker_style="spaced"` shows dB labels only on
  interval rows; `"all"` shows a label on every row.
- `apply_window` and `compute_fft_magnitude` are absent from `spectrum.py` and
  `mypy`/`ruff` pass cleanly.
- `_find_peak_row` and `_find_peak_row_index` use `bisect`, verified by a new
  test covering boundary values.
- Two concurrent calls to `_save_profile_export` targeting the same directory
  cannot write to the same file (verified by exclusive-open logic in tests).
- `CHANGELOG.md` and `SECURITY.md` exist at the repository root.
- `pytest-cov` is available as an optional dependency; `pytest --cov=eq_cli`
  runs without error after `pip install -e .[dev]`.
- `_frame_size_cache` and `_layout_cache` are capped at 8 entries.
- All existing 149 tests continue to pass.
- `ruff check .` and `mypy src` pass with no new errors.

## Results
- **m1**: Fixed `_show_db_marker` in `renderer.py`: `"all"` now generates labels
  for every row (via a full `_db_marker_labels` dict populated at construction)
  and always returns `True`; `"spaced"` correctly returns
  `row_index in self._db_marker_labels` (interval-aligned rows only).
- **m2**: Removed `apply_window` and `compute_fft_magnitude` from `spectrum.py`.
  Both were dead code: `SpectrumProcessor.process_frame` already inlines the
  windowing and FFT computation.  `magnitude_to_db` (which IS used by
  `_levels_to_db`) was retained.  Two tests confirm absence of the removed
  names.
- **m3**: Replaced the O(n) linear scan in `_find_peak_row` and the second
  O(n) `list.index()` call in `_find_peak_row_index` with `bisect.bisect_left`
  on a pre-computed ascending copy of the row-threshold list
  (`_row_thresholds_asc`).  Tests verify boundary values and index consistency.
- **m4**: Removed `_next_profile_export_path`.  `_save_profile_export` now
  uses an exclusive-create loop (`open(candidate, "x", encoding="utf-8")`) that
  atomically claims a numbered slot, eliminating the TOCTOU race.  Tests
  confirm that a pre-existing slot-001 causes the second writer to claim
  slot-002, and that `_next_profile_export_path` no longer exists.
- **m7**: Added `CHANGELOG.md` with entries from `v0.1.0` through `[Unreleased]`.
  Added `SECURITY.md` with a responsible-disclosure contact.  Added
  `[project.optional-dependencies]` `dev` group in `pyproject.toml` with
  `pytest-cov>=5` (plus `pytest`, `ruff`, `mypy`).
- **m10**: Converted `SpectrumProcessor._frame_size_cache` and
  `TerminalRenderer._layout_cache` to `collections.OrderedDict` with a max size
  of 8 entries and FIFO eviction via `popitem(last=False)`.  Two tests verify
  that both caches stay within the limit when forced past it.
- 10 new tests added across `test_renderer.py`, `test_spectrum.py`, and
  `test_loop.py`.

Local validation after all changes:
- `pytest`: 159 passed (10 new tests; 0 failures)
- `ruff check .`: passed
- `mypy src`: passed (no issues in 10 source files)

## Definition of Done
- All acceptance criteria met.
- Tests pass locally and in CI.
- Feature status updated to Completed.
