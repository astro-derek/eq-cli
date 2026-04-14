# Feature 0019: Chart Snapshot Save

## Status
Completed

## Objective
Add a single snapshot feature that lets users save the current terminal chart either from the CLI as a one-shot save flow or during live rendering via a runtime hotkey, using the existing render-frame and hotkey architecture rather than a separate export path.

## Scope
- Add a CLI-triggered snapshot flow for saving one rendered chart to disk and exiting cleanly.
- Add a runtime hotkey-triggered snapshot flow for saving the latest available chart without stopping the live session.
- Reuse the existing render frame as the source of truth so saved output matches the current chart layout, including title, axes, peak markers, and optional history rows.
- Add a snapshot serialization path that strips in-place redraw control sequences and can optionally preserve ANSI color codes.
- Add user-facing options for output target and format.
- Default output formats:
  - `txt`: plain text snapshot with no ANSI escape sequences; default and most portable.
  - `ansi`: terminal-colored text snapshot preserving ANSI styling for later viewing in ANSI-capable terminals.
- File naming strategy:
  - explicit path wins when provided
  - otherwise auto-name as `eq-cli-snapshot-YYYYMMDD-HHMMSS[-profile][-frozen].txt` or `.ansi`
  - sanitize profile/title fragments and keep names ASCII-safe

## Out of Scope
- PNG, SVG, or bitmap image export.
- Clipboard integration.
- Automatic periodic snapshots or recording a full session.
- Embedding metadata headers inside the saved chart body.
- Adding profile schema support for snapshot defaults in the first pass unless implementation stays trivial.

## Dependencies
- Existing terminal renderer and render frame model.
- Existing runtime hotkey handling and live loop state management.
- Existing history/peak/title rendering behavior, which should appear in snapshots unchanged.
- README/help text updates for the new save flows.

## Implementation Plan
1. Add snapshot CLI arguments with a minimal surface:
   - `--snapshot-file PATH` for one-shot save and exit.
   - `--snapshot-format txt|ansi` with `txt` as default.
   - `--snapshot-dir DIR` for runtime hotkey saves when repeated captures are expected.
2. Refactor rendering output so snapshot serialization is separate from live redraw control:
   - keep current in-place terminal redraw behavior for runtime.
   - add a stable snapshot serializer that renders the chart body without cursor-up or cursor-hide/show sequences.
   - optionally strip ANSI for `txt` output and preserve ANSI for `ansi`.
3. Extend hotkey support with `s` for snapshot:
   - map `s` to a new loop action.
   - update the on-screen shortcuts legend to include snapshot.
   - when pressed, save the most recent renderable frame if one exists.
4. Implement the CLI-triggered save flow:
   - resolve device and render settings normally.
   - capture until the first usable frame is available.
   - render once through the snapshot serializer.
   - write the file, print the saved path, and exit `0`.
5. Implement the runtime hotkey save flow:
   - use the latest cached frame already maintained by the loop.
   - save to explicit directory or current working directory with auto-generated filename.
   - avoid blocking the loop more than necessary; file write should be small because output is text.
6. Document behavior clearly:
   - one-shot CLI snapshot is for scripted capture.
   - runtime hotkey snapshot is for ad hoc saves during monitoring.
   - document default formats and naming behavior.

## TDD Tasks
1. Write failing parser tests for snapshot arguments and defaults.
2. Write failing loop tests for `s` hotkey mapping and no-op behavior when no frame is available.
3. Write failing renderer tests for snapshot serialization without redraw control sequences.
4. Write failing renderer tests for `txt` output stripping ANSI and `ansi` output preserving color when enabled.
5. Write failing CLI tests that verify one-shot snapshot mode writes a file and exits successfully.
6. Write failing integration-style loop tests that verify runtime snapshot saves the latest frame with the expected filename pattern.
7. Implement incrementally, then run targeted tests followed by the full suite.

## Acceptance Criteria
- A user can run a one-shot command to save a chart snapshot to disk and the process exits successfully after writing the file.
- A user can press `s` during live rendering to save the current chart without terminating the session.
- Saved snapshot content matches the visible chart layout for the current frame, including title, axes, peaks, and history when enabled.
- Plain text snapshots contain no ANSI or redraw control sequences.
- ANSI snapshots preserve chart coloring but still omit terminal cursor-control redraw prefixes.
- Auto-generated filenames are timestamped, deterministic in structure, and safe on macOS, Linux, and Windows.
- Help text and README examples document both save flows.

## Risks
- The current live renderer is optimized for in-place redraw, so snapshot export must avoid leaking cursor repositioning sequences into files.
- Runtime hotkey saves depend on a latest cached frame existing; early keypresses before first render need a clean no-op or status message.
- ANSI snapshots may look incorrect in editors that do not render escape codes.
- Large graph widths or future layout changes can make snapshot golden tests brittle unless assertions focus on stable content.
- Writing files directly in the render loop could briefly affect responsiveness if not kept minimal.

## Definition of Done
- Snapshot feature is implemented for both CLI-triggered and runtime-hotkey flows.
- Tests cover parser behavior, hotkey mapping, serialization, and file output.
- README and CLI help are updated.
- `features/implementation-checklist.md` is updated to mark the feature completed after acceptance criteria and tests pass.