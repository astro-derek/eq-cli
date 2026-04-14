# Implementation Checklist

This checklist is the working execution tracker for the MVP. It should be updated whenever feature status changes.

## Overall Status
- Discovery: completed
- MVP feature planning: completed
- MVP implementation: completed
- New features planning: completed
- New features implementation: completed

## Execution Order
- [x] Feature 0001: Project foundation and workflow
  - Status: completed
  - Goal: establish package structure, CLI entrypoint, and test/tooling baseline.
- [x] Feature 0002: Audio device discovery and selection
  - Status: completed
  - Goal: list input devices and support argument-driven or interactive selection.
- [x] Feature 0003: Real-time spectrum processing core
  - Status: completed
  - Goal: convert live audio frames into 32 log-spaced bands over 20 Hz to 20 kHz.
- [x] Feature 0004: CLI equalizer renderer
  - Status: completed
  - Goal: render live terminal bars with frequency and dB axes.
- [x] Feature 0005: Peak markers and visual stability
  - Status: completed
  - Goal: add gradual-decay peak markers and reduce flicker.
- [x] Feature 0006: Packaging and run instructions
  - Status: completed
  - Goal: support pip-based installation and documented run steps for Windows, macOS, and Linux.
- [x] Feature 0007: Tests, quality, and performance baseline
  - Status: completed
  - Goal: enforce tests, linting, typing, and a 20+ FPS baseline.

## New Features (Post-MVP Enhancement Phase)
- [x] Feature 0008: New features planning (planning phase)
  - Status: completed
  - Goal: organize ARCHITECTURE.md "New Features" into actionable tickets
- [x] Feature 0009: Theme capability system
  - Status: completed
  - Goal: customizable visual themes with color presets and overrides
- [x] Feature 0010: Centered title with version display
  - Status: completed
  - Goal: display "eq-cli v{version}" centered at top of graph
- [x] Feature 0011: Enhanced dB scale marker distance control
  - Status: completed
  - Goal: improve vertical axis marker density and visual options
- [x] Feature 0012: Improved axis labels and layout
  - Status: completed
  - Goal: enhance readability with units, frames, and color customization
- [x] Feature 0013: High-frequency registration bug investigation/fix
  - Status: completed
  - Goal: ensure frequencies and markers are represented between 10k and 20k
- [x] Feature 0014: Next-phase runtime enhancements
  - Status: completed
  - Goal: add profile discovery, peak hold, mode presets, runtime controls, shortcuts overlay, and stereo channel modes
- [x] Feature 0015: POSIX hotkey parity (Linux/macOS)
  - Status: completed
  - Goal: enable `f`/`r`/`q` runtime controls on POSIX terminals with safe terminal restore
- [x] Feature 0016: History view (waterfall/lightweight history)
  - Status: completed
  - Goal: add a temporal view of recent spectrum activity for short-term trend tracking
- [x] Feature 0017: Configurable history gradient
  - Status: completed
  - Goal: allow CLI/profile customization of history intensity character mapping
- [x] Feature 0018: Independent history color control
  - Status: completed
  - Goal: allow CLI/profile customization of history row color independently from active bars
- [x] Feature 0019: Chart snapshot save
  - Status: completed
  - Goal: save the current chart to disk either from a one-shot CLI flow or a runtime hotkey
- [x] Feature 0020: Spectrum processing refresh-rate headroom
  - Status: completed
  - Goal: profile and optimize the DSP hot path to improve refresh-rate headroom without changing behavior
- [x] Feature 0021: Renderer redraw headroom
  - Status: completed
  - Goal: reduce unnecessary terminal output by skipping identical frames and diffing changed lines
- [x] Feature 0022: Renderer ANSI serialization headroom
  - Status: completed
  - Goal: reduce changed-frame renderer CPU and output size by avoiding per-cell ANSI wrapping for contiguous color spans
- [x] Feature 0023: Renderer logical row reuse
  - Status: completed
  - Goal: avoid rebuilding unchanged logical chart rows during live redraws and compare the new result against the original renderer benchmark
- [x] Feature 0024: Deployment and distribution automation
  - Status: completed
  - Goal: build deployable Python artifacts from CI and Git tags, and document the release process
- [x] Feature 0025: Code quality and stability fixes
  - Status: completed
  - Goal: address six high-priority issues from senior developer review (bugs C2/C3, cross-validation M3, release hardening M7/M8, deferred import C1, RenderConfig dataclass M4, table-driven merge M5)
- [x] Feature 0026: Remaining code review items
  - Status: completed
  - Goal: address the six items deferred from feature-0025 (m1 marker style bug, m2 dead code, m3 O(n) scan, m4 TOCTOU race, m7 missing docs/cov, m10 unbounded caches)

## Update Rules
- Mark a feature in progress when implementation begins.
- Mark a feature completed only after its acceptance criteria and tests pass.
- If scope changes, update both this checklist and the corresponding feature document.