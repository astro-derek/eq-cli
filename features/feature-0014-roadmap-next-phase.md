# Feature 0014: Next-Phase Roadmap

## Status
Phase 4 completed

## Goal
Define and execute the next practical improvements after the current profiling/theme and axis work.

## Roadmap

1. Profile Discoverability (Phase 1)
- Add `--list-profiles` to print built-in profile names and exit.
- Keep behavior simple and script-friendly.

2. Peak Hold (Phase 1)
- Add configurable peak hold frames to delay peak decay.
- Add `--peak-hold-frames` CLI option.
- Support profile default via `peak_hold_frames`.

3. Runtime Presets (Phase 2)
- Add optional `--mode studio|live|debug` convenience switches.
- Define override precedence with explicit CLI args.
- Startup prints active mode/profile/render settings.

4. Runtime Controls (Phase 2)
- Add keyboard controls for freeze/reset/quit during live rendering.

4. Stereo Analysis (Phase 3)
- Add stereo capture and display modes: L/R, sum, mid/side.

5. Cross-Platform Hotkeys (Phase 3)
- Add Linux/macOS runtime hotkey support to match Windows (`f`, `r`, `q`).

6. History View (Phase 4)
- Add lightweight scrolling history or waterfall-style visualization.

## Implementation Started
- [x] Create roadmap document.
- [x] Implement `--list-profiles`.
- [x] Implement `--peak-hold-frames` and profile support.
- [x] Implement `--mode studio|live|debug` presets with explicit CLI precedence.
- [x] Add startup telemetry printout for active rendering settings.
- [x] Add runtime keyboard controls (`f`, `r`, `q`) for live rendering.
- [x] Add on-screen shortcuts/status legend (`[F] Freeze: ON/OFF`, `[R] Reset Peaks`, `[Q] Quit`).
- [x] Add `--no-shortcuts` / profile `show_shortcuts` configurability.
- [x] Add `--channel-mode mono|left|right|sum|mid|side` stereo analysis support.
- [x] Expose `channel_mode` in profiles and mode presets.
- [x] Add Linux/macOS (POSIX) hotkey support for `f`, `r`, `q`.
- [x] Add history view via `--history-rows` with profile support.
- [x] Add configurable history gradient via `--history-gradient` and profiles.
- [x] Add independent history row coloring via `--color-history` and profile colors.
- [x] Update docs.
- [x] Validate tests/lint/types (104 tests, 0 failures).
