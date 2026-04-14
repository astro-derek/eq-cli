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

## Update Rules
- Mark a feature in progress when implementation begins.
- Mark a feature completed only after its acceptance criteria and tests pass.
- If scope changes, update both this checklist and the corresponding feature document.