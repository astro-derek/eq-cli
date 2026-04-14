# Feature 0000: Discovery - Real-Time CLI Equalizer

## Status
Discovery complete

## Problem Statement
Build a Python application that captures live audio from a selected input source and renders a real-time equalizer view, with frequency on the horizontal axis and loudness on the vertical axis.

## Constraints
- Python implementation.
- First pass is a CLI interface.
- Include colors, peak marker per frequency, and axis labels for kHz and dB.
- Allow selecting any available audio input source.
- Frequency axis requirement currently states "20kHz to 20000kHz".
- Frequency axis must be logarithmic.
- Deliver as a single deployable package with dependencies.

## Confirmed Decisions (From Clarifications)
- Frequency range: 20 Hz to 20 kHz.
- MVP interface: terminal-only real-time graph.
- Target platforms: Windows, macOS, Linux.
- Input scope for MVP: microphone/input devices only (no loopback requirement).
- Real-time threshold: at least 20 updates per second.
- Device selection UX: both CLI argument and interactive prompt.
- Default visualization resolution: 32 frequency bands.
- Peak behavior: gradual decay.
- Color fallback: automatic monochrome fallback when color is unsupported.
- Packaging acceptance for MVP: Python app with pip install instructions is acceptable.

## Remaining Open Items
1. Long-term standalone GUI scope is deferred; CLI remains MVP.

## Initial MVP Scope
- Enumerate and select input device from CLI.
- Capture live audio stream.
- Compute FFT and map bins on a logarithmic frequency axis.
- Convert magnitude to dB-like display values.
- Render live CLI equalizer with color, monochrome fallback, axis labels, and per-band peak marker.
- Use 32 log-spaced bands over 20 Hz to 20 kHz.
- Achieve at least 20 FPS update rate in normal operation.
- Package in a format to be finalized after packaging decision.
- Package as a Python application with documented pip-based setup for MVP.

## Candidate Feature Breakdown
1. feature-0001: Project foundation and workflow setup.
2. feature-0002: Audio device discovery and selection.
3. feature-0003: Real-time spectrum processing core.
4. feature-0004: CLI equalizer rendering.
5. feature-0005: Peak marker behavior and visual stability.
6. feature-0006: Single-artifact packaging.
7. feature-0007: Tests and performance baseline.

## Discovery Exit Criteria
- Frequency-axis units/range is confirmed.
- Target OS matrix for packaging is confirmed.
- Definition of "single deployable package" is confirmed.
- MVP interaction model (flags, prompts, or both) is confirmed.
- Baseline real-time acceptance thresholds are confirmed.

## Discovery Progress
- Confirmed: frequency range, interface mode, platform scope, input scope, runtime UX, default band count, peak behavior, color fallback, and baseline update-rate target.
- Pending: final packaging acceptance definition.
- No blocking discovery items remain.
