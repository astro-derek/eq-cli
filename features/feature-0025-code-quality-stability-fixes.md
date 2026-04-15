# Feature 0025: Code Quality and Stability Fixes

## Status
Completed

## Objective
Address six high-priority issues identified in a senior developer review of the
codebase. The fixes eliminate user-facing bugs, guard against invalid input,
harden the release pipeline, and reduce long-term maintenance risk.

## Scope

### Priority 1 — C2: Exported profile with `block_size=None` breaks re-import
`_build_export_profile` unconditionally writes `"block_size": args.block_size`
even when `args.block_size` is `None`. The resulting `"block_size": null` in
the JSON causes `_validate_int` to raise `ValueError` on reload, silently
corrupting every exported profile where `--block-size` was not set.

**Fix:** Remove `block_size` from the initial profile dict literal; keep only the
conditional insertion that already exists on lines 629–630.

### Priority 2 — C3: `--db-interval 0` causes unhandled `ZeroDivisionError`
Passing `--db-interval 0` (or `"db_interval": 0` in a profile) propagates to
`_default_graph_height` in `renderer.py`, which divides by `db_interval`. The
broad `except Exception` in `run_equalizer` catches the crash but produces a
confusing message with no actionable guidance.

**Fix:** Add a positivity guard in `_merge_profile_settings` (CLI path) and in
`_validate_profile` (profile file path).

### Priority 3 — M3: `db_min >= db_max` produces a silently broken display
No cross-parameter validation prevents `db_min >= db_max`. Passing
`--db-min 0 --db-max -10` results in a nonsense one-row graph with no error.

**Fix:** After all CLI and profile values are merged, validate
`args.db_min < args.db_max`.

### Priority 4 — M7/M8: Release workflow publishes without running tests; action not pinned
The release workflow builds and publishes artifacts without first running
`pytest`, `ruff`, or `mypy`. A broken tagged commit will produce broken
published artifacts. Additionally, `softprops/action-gh-release@v2` is a
mutable tag, which is a supply-chain risk.

**Fix:** Add test, lint, and type-check steps to the release workflow before the
build step. Install the PortAudio system dependency required by `sounddevice`.
Pin the `softprops/action-gh-release` action to a commit SHA.

### Priority 5 — C1: Top-level `sounddevice` import crashes import on machines without PortAudio
`import sounddevice as sd` at the top of `loop.py` raises `OSError: PortAudio
library not found` at import time on any machine without the native PortAudio
library. Because `cli.py` imports `loop.py`, test collection fails completely
on affected machines (CI without `libportaudio2`, Docker images, etc.).

**Fix:** Defer the import to the point of use inside `run_equalizer()`,
consistent with the pattern already used in `audio.py`.

### Priority 6 — M4/M5: 33-parameter function and copy-paste merge blocks
`run_equalizer` accepts 33 individual keyword arguments, making the public API
difficult to read, test, and extend. `_merge_profile_settings` contains 25+
near-identical copy-paste if-blocks; adding any profile field requires changes
in at least five places.

**Fix (M4):** Introduce a frozen `RenderConfig` dataclass that groups all display
and rendering parameters. Update `run_equalizer` to accept
`(device, config: RenderConfig)`. Update `cli.py` to construct and pass the
dataclass.

**Fix (M5):** Replace the copy-paste merge blocks in `_merge_profile_settings`
with type-grouped module-level tables (`_PROFILE_FLOAT_FIELDS`,
`_PROFILE_INT_FIELDS`, `_PROFILE_STR_FIELDS`, `_PROFILE_BOOL_FIELDS`,
`_COLOR_FIELDS`) and corresponding loops.

## Out of Scope
- Fixing the incomplete `'all'` vs `'spaced'` db marker feature (m1).
- Removing dead code in `spectrum.py` (m2).
- Replacing the O(n) scan in `_find_peak_row` (m3).
- TOCTOU race in `_next_profile_export_path` (m4).
- Unbounded caches (m10).
- Adding `CHANGELOG.md`, `SECURITY.md`, or pytest-cov (m7).

## Dependencies
- All existing features (this is a cross-cutting maintenance release).

## Implementation Plan
1. Create this feature document.
2. Fix C2 in `cli.py:_build_export_profile`.
3. Fix C3 in `cli.py:_merge_profile_settings` and `profile.py:_validate_profile`.
4. Fix M3 in `cli.py:_merge_profile_settings` (cross-field validation after merge).
5. Harden `release.yml` (M7: add test steps; M8: pin action SHA).
6. Fix C1 in `loop.py` (defer `sounddevice` import).
7. Implement M4: `RenderConfig` dataclass in `loop.py`; update `run_equalizer`; update `cli.py`.
8. Implement M5: table-driven `_merge_profile_settings` in `cli.py`.
9. Add tests for all behaviour changes.
10. Verify `pytest`, `ruff`, and `mypy` all pass.

## Acceptance Criteria
- Exporting a profile without `--block-size` produces a valid JSON that can be re-imported.
- `eq-cli --db-interval 0` exits with a clear error, not a `ZeroDivisionError`.
- A profile file with `"db_interval": 0` fails validation with a clear error.
- `eq-cli --db-min 0 --db-max -10` exits with a clear error.
- The release workflow runs tests before building artifacts.
- The release workflow's third-party action is pinned to a commit SHA.
- `import eq_cli.loop` succeeds on a machine without PortAudio installed.
- `run_equalizer` accepts a `RenderConfig` dataclass instead of 33 keyword arguments.
- `_merge_profile_settings` uses a table-driven approach with no copy-paste merge blocks.
- All existing tests continue to pass.
- `ruff check .` passes with no new violations.
- `mypy src` passes with no new errors.

## Results
- **C2**: Removed the unconditional `"block_size": args.block_size` from the
  initial `_build_export_profile` dict literal. `block_size` is now only
  included in the exported JSON when the user explicitly sets `--block-size`,
  preventing a `ValueError` on re-import of every auto-generated profile.
- **C3**: Added `args.db_interval <= 0` guard in `_merge_profile_settings`
  (CLI path) and a matching `db_interval > 0` positivity check in
  `_validate_profile` inside `profile.py` (profile-file path).  `db_interval`
  was removed from `_PROFILE_NUMERIC_KEYS` and added to
  `_PROFILE_SPECIAL_NUMERIC_KEYS` so it remains in the allowed-key set while
  receiving the positivity check.
- **M3**: Added `args.db_min >= args.db_max` cross-parameter guard at the end
  of `_merge_profile_settings`, after CLI and profile values are merged.
- **M7**: Added PortAudio system-dependency install, `pytest`, `ruff`, and
  `mypy` steps to `release.yml` before the build step so broken commits cannot
  produce released artifacts.
- **M8**: Pinned `softprops/action-gh-release` to commit SHA
  `3bb12739c298aeb8a4eeaf626c5b8d85266b0e65` (v2.6.2) in `release.yml`.
- **C1**: Moved `import sounddevice as sd` from module level to inside
  `run_equalizer()`.  Because `from __future__ import annotations` is already
  present, the `sd.CallbackFlags` type annotation in the nested callback is
  safe.  This prevents `OSError: PortAudio library not found` from propagating
  at import time on machines without PortAudio installed.
- **M4**: Introduced a frozen `RenderConfig` dataclass in `loop.py` that groups
  all 32 rendering/display parameters.  `run_equalizer` now accepts
  `(device: AudioInputDevice, config: RenderConfig | None = None)`.  `cli.py`
  constructs a `RenderConfig` and passes it.  The test fakes in
  `test_devices.py` were updated to accept the new positional signature and use
  `dataclasses.asdict` to expand config fields for assertion.
- **M5**: Replaced the 25+ copy-paste if-blocks in `_merge_profile_settings`
  with five module-level tables (`_PROFILE_FLOAT_FIELDS`,
  `_PROFILE_INT_FIELDS`, `_PROFILE_STR_FIELDS`, `_PROFILE_BOOL_FIELDS`,
  `_COLOR_FIELDS`) and corresponding loops.  The merge block shrank from
  ~120 lines to ~30 lines.
- 9 new tests added covering C2 (round-trip export), C3 (zero/negative
  `db_interval`), M3 (invalid `db_min`/`db_max` pairs), and profile-file
  validation for C3.

Local validation after all changes:
- `pytest`: 149 passed (9 new tests; 0 failures)
- `ruff check .`: passed
- `mypy src`: passed (no issues in 10 source files)

## Risks
- M4 (`RenderConfig`) changes the public function signature of `run_equalizer`.
  All call sites (only `cli.py` in production code) must be updated in the same
  commit to avoid a broken intermediate state.
- M5 must preserve exact semantics of the existing merge logic; each table entry
  must be verified against the original if-block it replaces.

## Definition of Done
- All acceptance criteria met.
- Tests pass locally and in CI.
- Feature status updated to Completed.
