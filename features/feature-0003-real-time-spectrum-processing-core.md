# Feature 0003: Real-Time Spectrum Processing Core

## Status
Completed

## Objective
Build a streaming DSP pipeline that converts live audio frames into 32 log-spaced bands over 20 Hz to 20 kHz, expressed in dB for rendering.

## Scope
- Frame ingestion interface from audio stream.
- Windowing and FFT.
- Log-frequency band aggregation.
- dB conversion suitable for display.
- Processing loop support for at least 20 updates per second.

## Out of Scope
- Terminal rendering details.
- Peak marker visualization behavior.

## Dependencies
- Feature 0001.
- Feature 0002 (selected device stream source).

## Implementation Plan
1. Define typed data models:
   - AudioFrame
   - SpectrumBands
2. Implement pure functions:
   - apply_window
   - compute_fft_magnitude
   - map_to_log_bands(20Hz-20kHz, 32 bands)
   - magnitude_to_db
3. Create processing service that consumes frames and emits bands.
4. Add rate controls and buffering strategy to sustain update budget.

## TDD Tasks
1. Write failing tests for log-band boundaries and band count.
2. Write failing tests for dB conversion monotonicity and floor handling.
3. Write failing tests for processing loop throughput with synthetic frames.
4. Implement pure DSP functions to satisfy tests.
5. Implement processing service and frame pipeline.
6. Run targeted tests, then full suite.

## Acceptance Criteria
- Exactly 32 log-spaced bands cover 20 Hz to 20 kHz.
- dB output is stable and bounded for silence/low amplitudes.
- Pipeline handles synthetic stream at 20+ updates/sec under baseline load.
- Core DSP functions are unit-tested and deterministic.

## Risks
- Numerical instability near silence without proper floor.
- Throughput regressions with suboptimal buffer sizes.

## Definition of Done
- All DSP acceptance tests pass.
- Performance baseline test passes at target threshold.
