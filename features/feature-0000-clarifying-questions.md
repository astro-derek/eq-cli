# Feature 0000: Clarifying Questions

## Resolution Summary
- Frequency range: 20 Hz to 20 kHz.
- MVP interface: terminal-only.
- Target OS: Windows, macOS, Linux.
- Audio source scope: microphone/input devices only.
- Real-time target: at least 20 updates/second.
- Device selection: CLI argument and interactive prompt.
- Default band count: 32.
- Peak behavior: gradual decay.
- Color fallback: automatic monochrome fallback.
- Packaging decision: Python app + pip install instructions is acceptable for MVP.

## Priority 1
1. Should the frequency range be interpreted as 20 Hz to 20 kHz, or do you explicitly want 20 kHz to 20000 kHz?
2. Is terminal-based visualization sufficient for MVP, with GUI deferred to a later phase?
3. What does "single deployable package" mean for acceptance: one executable, installer, or zipped bundle?

## Priority 2
4. Which operating systems must MVP support (Windows only or cross-platform)?
5. Should audio capture support microphone/input only, or also system/loopback audio in MVP?
6. What minimum update rate or latency should define "real-time" for acceptance?

## Priority 3
7. For device selection, do you want CLI arguments, interactive selection, or both?
8. How many frequency bins/bands should the CLI graph show by default?
9. How should peak markers decay: hold-then-drop, gradual decay, or immediate falloff?
10. Do you need explicit fallback behavior when terminal color support is unavailable?
