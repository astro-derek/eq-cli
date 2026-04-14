# Feature 0023: Renderer Logical Row Reuse

## Status
Completed

## Objective
Reduce changed-frame live render CPU by reusing unchanged logical chart rows instead of rebuilding the full graph on every moving frame.

## Scope
- Add a test that proves minimally changed frames do not rebuild every graph row.
- Reuse previously rendered logical lines when geometry and static renderer settings remain stable.
- Rebuild only the graph rows, history rows, and shortcut line entries that actually changed.
- Re-run the original renderer and spectrum comparison benchmark after the optimization.

## Out of Scope
- Terminal backend replacement or curses migration.
- New renderer features or chart layout changes.
- DSP-path behavior changes beyond the final comparison benchmark.

## Dependencies
- Existing redraw and serializer work in `src/eq_cli/renderer.py`.
- Renderer tests in `tests/test_renderer.py`.
- Existing spectrum/original-baseline comparison script logic from Features 0020-0022.

## Implementation Plan
1. Add a failing renderer test for minimally changed frames rebuilding fewer bar rows.
2. Add reusable line/row caching to the live renderer path when the prior frame geometry is still valid.
3. Rebuild only changed graph rows and other dynamic lines.
4. Re-run full validation.
5. Re-run the original benchmark comparison and capture the new results.

## Acceptance Criteria
- Minimally changed frames rebuild fewer bar rows than the total graph height.
- Identical-frame fast-path behavior remains unchanged.
- Snapshot rendering remains correct.
- Full test suite, Ruff, and mypy pass.
- Updated benchmark notes compare the current renderer against the original baseline.

## Results
- Added a renderer regression test that proves a minimally changed live frame rebuilds fewer graph rows than the full graph height.
- Added selective live logical-line reuse in the renderer so unchanged graph rows, static axis/title lines, unchanged history rows, and an unchanged shortcuts line are reused from the previous render state.
- Preserved the existing identical-frame fast path and snapshot behavior.
- Final combined original-like comparison results for the dense benchmark case (`graph_width=140`, `graph_height=24`, labels, history, color, peak labels, `band_gap=1`) were:
	- spectrum original-like total: about `0.0459s`
	- spectrum current total: about `0.0139s`
	- spectrum speedup: about `3.29x`
	- renderer original-like full repaint output: about `20078` bytes
	- renderer original-like changed-frame output: about `19682` bytes
	- renderer current full repaint output: about `6533` bytes
	- renderer current changed-frame output: about `4888` bytes
	- renderer current identical-frame output: `0` bytes
	- renderer original-like changed-frame CPU: about `1.244s` for `2000` renders
	- renderer current changed-frame CPU: about `1.123s` for `2000` renders
	- renderer changed-frame CPU speedup vs original-like baseline: about `1.11x`
- Validation passed with `140` tests, Ruff, and mypy all green.

## Risks
- Changed-frame rendering still computes bar content for each changed row in Python, so there is additional headroom if renderer CPU becomes the next bottleneck again.
- The current reuse path assumes stable line counts; when rendered line count changes, the renderer correctly falls back to a full rebuild.

## Definition of Done
- Row-reuse regression coverage is in place.
- Live renderer logical row reuse is implemented.
- Original-baseline comparison numbers are captured.
- The implementation checklist is updated after validation passes.