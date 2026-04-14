# Feature 0021: Renderer Redraw Headroom

## Status
Completed

## Objective
Profile and optimize the live terminal redraw path to reduce unnecessary output and improve refresh-rate headroom without changing the visible chart.

## Scope
- Measure current renderer output size and render behavior for realistic dense frames.
- Avoid emitting terminal output for identical consecutive frames.
- Update only changed lines after the first render instead of always repainting the full chart.
- Preserve first-render behavior and snapshot serialization behavior.

## Out of Scope
- Character-level diffing within a single line.
- Terminal backend replacement or curses migration.
- Changing the visible chart layout or ANSI style model.

## Dependencies
- Existing renderer line assembly in `src/eq_cli/renderer.py`.
- Existing renderer tests in `tests/test_renderer.py`.

## Implementation Plan
1. Measure current renderer cost and output size for a dense frame.
2. Add tests for repeated identical frames and changed-frame partial redraw behavior.
3. Store the previous rendered lines and compare them against the new frame.
4. Emit nothing for identical consecutive frames.
5. Emit cursor-motion plus line-clear updates only for changed lines when line count is stable.
6. Re-run full validation and capture before/after output-size numbers.

## Acceptance Criteria
- Consecutive identical frames emit no redraw output.
- Changed frames emit a partial redraw sequence rather than a full repaint when line count is unchanged.
- Snapshot rendering remains unaffected.
- Full test suite, Ruff, and mypy pass.

## Results
- Added diff-based live redraw behavior in `TerminalRenderer`.
- Added an exact-frame fast path that returns immediately for identical consecutive live frames.
- Added cached static per-frequency layout data so axis/layout work is not recomputed for stable frequency geometry.
- Identical consecutive frames now emit `0` bytes.
- In a dense local benchmark frame (`graph_width=140`, `graph_height=24`, labels, history, color, peak labels), output sizes were:
  - full repaint: about `20078` bytes
  - unchanged frame: `0` bytes
  - minimally changed frame: about `17938` bytes
- In local CPU timing for `2000` repeated renders of that dense frame:
  - original-like full repaint path: about `1.40s`
  - current identical-frame path: about `0.0002s`
  - current minimally changed alternating-frame path: about `1.43s`

## Risks
- Line-count changes still fall back to a full repaint path.
- CPU-side rendering still rebuilds the logical frame before diffing, so the main win here is reduced terminal output rather than reduced string-generation cost.

## Definition of Done
- Diff-based redraw is implemented and tested.
- Local output-size measurements are captured.
- The implementation checklist is updated after validation passes.