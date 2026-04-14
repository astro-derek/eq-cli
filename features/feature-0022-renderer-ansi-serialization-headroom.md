# Feature 0022: Renderer ANSI Serialization Headroom

## Status
Completed

## Objective
Profile and optimize the changed-frame renderer path by reducing the cost of ANSI color serialization without changing the visible chart.

## Scope
- Measure the current changed-frame renderer hot path after Feature 0021.
- Replace per-cell ANSI wrapping with contiguous run-based ANSI serialization.
- Preserve monochrome rendering, snapshots, and the visible colored chart output.

## Out of Scope
- Terminal backend replacement or curses migration.
- Visual chart layout changes.
- DSP or audio callback changes.

## Dependencies
- Existing renderer implementation in `src/eq_cli/renderer.py`.
- Existing renderer tests in `tests/test_renderer.py`.

## Implementation Plan
1. Add a renderer test that encodes the expected contiguous-run ANSI output behavior.
2. Change bar-row serialization to emit one ANSI wrapper per contiguous run instead of per cell.
3. Benchmark the changed-frame renderer path before and after the change.
4. Re-run targeted tests plus full validation.

## Acceptance Criteria
- Colored bar rows preserve the same visible content as before.
- Contiguous same-color spans are serialized with one ANSI wrapper per run.
- Changed-frame renderer CPU and/or output size improves in local benchmarks.
- Full test suite, Ruff, and mypy pass.

## Results
- Added a regression test that locks in contiguous ANSI run serialization for colored bar rows.
- Added cached contiguous band spans to the renderer layout so bar rows and history rows can be filled with chunked slice assignments instead of per-column Python loops.
- Dense local renderer measurements for `graph_width=140`, `graph_height=24`, labels, history, color, peak labels, and `band_gap=1` now show:
	- full repaint output: about `6533` bytes
	- minimally changed frame output: about `4888` bytes
	- alternating changed-frame render CPU: about `1.36s` for `2000` renders
- Compared with the earlier renderer-redraw pass on the same dense scenario:
	- minimally changed frame output dropped from about `17938` bytes to about `4888` bytes
	- alternating changed-frame render CPU improved from about `1.43s` to about `1.36s` for `2000` renders
- Validation passed with `139` tests, Ruff, and mypy all green.

## Risks
- The renderer still rebuilds logical rows before diffing, so there is more headroom available if changed-frame CPU becomes the next target again.
- The grouped ANSI serializer slightly favors lower terminal output volume over the absolute minimum pure-Python string-building cost, which is the right tradeoff for live terminal redraws.

## Definition of Done
- Contiguous ANSI serialization is implemented and covered by tests.
- Chunked band-span filling is implemented for bar rows and history rows.
- Local benchmark results are captured.
- The implementation checklist is updated after validation passes.