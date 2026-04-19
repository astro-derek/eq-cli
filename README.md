# eq-cli

Terminal-based real-time equalizer for live audio input.

## Installation

### Requirements

- Python 3.12 or newer
- pip
- A virtual environment for installation on macOS and most Linux distributions

### Step 1. Create and activate a virtual environment

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

On macOS, Python installed via Homebrew is usually an externally managed
environment. Installing with `pip install .` against the system interpreter can
fail with `externally-managed-environment`. Use a virtual environment instead.

### Step 2. Install the package

```sh
python -m pip install .
```

### Step 3. Verify the install

```sh
eq-cli --help
```

## Usage

`eq-cli` captures live input from your selected device and renders a real-time
spectrum in the terminal. A typical workflow is: pick a device, choose a
profile or mode, then tune behavior with options like refresh rate, labels,
history rows, and colors.

The examples below are grouped by common tasks so you can copy a baseline
command and then layer additional options as needed.

### List available audio input devices

```sh
eq-cli --list-devices
```

### List built-in profiles

```sh
eq-cli --list-profiles
```

### Apply convenience mode presets

```sh
eq-cli --device <identifier-or-name> --mode studio
eq-cli --device <identifier-or-name> --mode live
eq-cli --device <identifier-or-name> --mode debug
```

Mode behavior:

- `studio`: defaults toward analysis (`profile=studio`, `volume_mode=absolute`)
- `live`: defaults toward responsiveness (`refresh_rate=60`, light peak hold)
- `debug`: high-visibility labels/markers for inspection

Explicit CLI flags take precedence over mode defaults.

### Start the equalizer with a specific device

```sh
eq-cli --device <identifier-or-name>
```

### Control redraw rate (for example, 60 Hz)

```sh
eq-cli --device <identifier-or-name> --refresh-rate 60
```

Note: higher refresh rates increase CPU usage and may require smaller stream
blocks; this tool automatically adjusts stream block size based on the chosen
refresh rate.

### Set an explicit audio block size

```sh
eq-cli --device <identifier-or-name> --block-size 2048
```

`--block-size` overrides the auto-tuned audio callback size when you want more
direct control over latency and stability.

### Apply a gain offset

```sh
eq-cli --device <identifier-or-name> --gain 6
```

`--gain` applies an additive dB offset to all display levels without changing
the underlying signal. Use it to shift the entire spectrum up or down when the
input is very quiet or very hot.

### Select volume mode

```sh
eq-cli --device <identifier-or-name> --volume-mode relative
eq-cli --device <identifier-or-name> --volume-mode absolute
```

`--volume-mode` controls how the spectrum level is mapped to the dB scale:

- `relative`: the loudest band is always stretched to fill the top of the range,
  so the graph always looks active regardless of actual signal level. Good for
  everyday monitoring.
- `absolute`: levels are mapped directly to dB values, so the display falls quiet
  when the signal is soft and shows the true effect of gain changes or filter
  sweeps over time. Preferred for studio or diagnostic use.

### Save a one-shot chart snapshot

```sh
eq-cli --device <identifier-or-name> --snapshot-file snapshots/current.txt
eq-cli --device <identifier-or-name> --snapshot-file snapshots/current.ansi --snapshot-format ansi
```

`--snapshot-file` captures the first usable chart frame, writes it to disk, and
exits. Use `--snapshot-format txt` for plain text or `--snapshot-format ansi`
to preserve terminal color codes.

### Set graph dimensions

```sh
eq-cli --device <identifier-or-name> --graph-height 14
eq-cli --device <identifier-or-name> --graph-width 140
```

`--graph-height` controls the number of rendered spectrum rows. If omitted, the
height is derived from the current dB scale. `--graph-width` sets the horizontal
character width of the graph area (default: 120).

### Set the dB display range

```sh
eq-cli --device <identifier-or-name> --db-min -60 --db-max 0
eq-cli --device <identifier-or-name> --db-min -80 --db-max 6 --db-interval 6
```

`--db-min` sets the bottom of the dB scale (default: -80) and `--db-max` sets
the top (default: 6); `--db-min` must be less than `--db-max`. `--db-interval`
controls the row spacing in dB (default: 10); smaller intervals produce more
rows and finer vertical resolution. The interval must be greater than zero.

### Enable axis labels (opt-in)

```sh
eq-cli --device <identifier-or-name> --axis-labels
```

When axis labels are enabled, matching notches are drawn on the horizontal and
vertical axes so labeled frequencies and dB markers are easier to follow.

### Use custom horizontal label frequencies

```sh
eq-cli --device <identifier-or-name> --axis-labels --axis-frequencies 50,100,200,500,1000,5000
```

`--axis-frequencies` accepts a comma- or space-separated list of frequencies in
Hz. Labels outside the visible analysis range are skipped automatically.

### Show numeric dB labels on peak markers

```sh
eq-cli --device <identifier-or-name> --peak-db-labels
```

`--peak-db-labels` overlays rounded absolute peak dB values above the matching peak band
when that band is wide enough and there is a free row above the peak. Use
`--no-peak-db-labels` to explicitly disable them when a profile enables them.

### Configure title and dB marker style

```sh
eq-cli --device <identifier-or-name> --no-title --db-marker-style minimal
eq-cli --device <identifier-or-name> --graph-height 12 --db-marker-style all
eq-cli --device <identifier-or-name> --title-text "My Studio"
```

`--db-marker-style` controls how many dB rows get a numeric label:

- `all`: every row has a dB marker
- `spaced`: markers appear at intervals (default)
- `minimal`: only the most significant rows are labeled, reducing visual clutter

`--title-text` overrides the centered title string shown at the top of the
graph. The default title is `eq-cli v<version>`. Use `--no-title` to hide the
title entirely.

### Configure peak hold behavior

```sh
eq-cli --device <identifier-or-name> --peak-hold-frames 12
```

`--peak-hold-frames` controls how many rendered frames a peak marker is held
before it starts decaying.

### Select stereo analysis mode

```sh
eq-cli --device <identifier-or-name> --channel-mode mono
eq-cli --device <identifier-or-name> --channel-mode left
eq-cli --device <identifier-or-name> --channel-mode right
eq-cli --device <identifier-or-name> --channel-mode sum
eq-cli --device <identifier-or-name> --channel-mode mid
eq-cli --device <identifier-or-name> --channel-mode side
```

`--channel-mode` controls how input channels are analyzed for the spectrum.

### Enable history view (lightweight waterfall)

```sh
eq-cli --device <identifier-or-name> --history-rows 6
eq-cli --device <identifier-or-name> --history-rows 6 --history-gradient " .:-=+*#%@"
eq-cli --device <identifier-or-name> --history-rows 6 --color-history yellow
```

`--history-rows` adds recent spectrum rows below the main plot. Set `0` to
disable history output.

`--history-gradient` controls the character ramp used by the history view from
low to high intensity.

`--color-history` controls the color of history rows independently from live
bar color.

### Set frequency band gap

```sh
eq-cli --device <identifier-or-name> --band-gap 1
```

`--band-gap` inserts a separator of the given width (in characters) between
labeled frequency regions, making the bands visually easier to distinguish.
Default is 0 (no gap).

### Customize bar and peak characters

```sh
eq-cli --device <identifier-or-name> --bar-char "="
eq-cli --device <identifier-or-name> --peak-char "_"
```

`--bar-char` sets the character used to draw active spectrum bars (default:
`#`). `--peak-char` sets the character used for peak markers (default: `-`).

### Use a named profile from a profile file

```sh
eq-cli --device <identifier-or-name> --profile-file profiles/theme_profiles.json --profile studio
```

Profile files carry both visual styling and runtime tuning values. Supported
keys include: `gain`, `db_min`, `db_max`, `db_interval`, `refresh_rate`,
`block_size`, `graph_height`, `graph_width`, `band_gap`, `axis_labels`,
`axis_frequencies`, `bar_char`, `peak_char`, `peak_hold_frames`,
`peak_db_labels`, `history_rows`, `history_gradient`, `show_shortcuts`,
`title`, `title_text`, `volume_mode`, `channel_mode`, `db_marker_style`,
`snapshot_file`, `snapshot_format`, `snapshot_dir`, and `colors`.

### Use a built-in profile directly

```sh
eq-cli --device <identifier-or-name> --profile studio
```

Built-in profiles:

- `default`: current standard layout and colors
- `studio`: tall wide graph, no history rows, underscore peak markers, minimal dB markers, bright colors, `absolute` volume mode, `db_min=-76`, `db_max=0`, `peak_hold_frames=12`, runtime snapshots default to ANSI format in `snapshots/`
- `green-based`: green-focused profile with axis/labels/bars/history in green tones and `peak_hold_frames=6`
- `minimal`: compact monochrome-style layout with minimal labeling
- `high-contrast`: labels on, dense markers, strong contrast colors, `peak_hold_frames=4`
- `neon-night`: vivid cyan/magenta/yellow palette with extra peak hold and history rows
- `sunset-drive`: warm retro palette with magenta bars, red peaks, and cyan history

Example invocations:

```sh
eq-cli --device <identifier-or-name> --profile default
eq-cli --device <identifier-or-name> --profile studio
eq-cli --device <identifier-or-name> --profile green-based
eq-cli --device <identifier-or-name> --profile minimal
eq-cli --device <identifier-or-name> --profile high-contrast
eq-cli --device <identifier-or-name> --profile neon-night
eq-cli --device <identifier-or-name> --profile sunset-drive
```

### Studio recommendation

For studio work such as checking the effect of a filter sweep on the audio
signal, use `absolute` volume mode so boosts and cuts remain meaningful over
time instead of being re-normalized every frame (see [Select volume mode](#select-volume-mode)).
The built-in `studio` profile enables this automatically:

```sh
eq-cli --device <identifier-or-name> --profile studio
```

### Override profile colors from CLI

```sh
eq-cli --device <identifier-or-name> --profile-file profiles/theme_profiles.json --profile studio --color-axis 90 --color-label bright_white --color-bar cyan --color-peak red
eq-cli --device <identifier-or-name> --profile-file profiles/theme_profiles.json --profile studio --color-history yellow
```

The same overrides work with built-in profiles:

```sh
eq-cli --device <identifier-or-name> --profile high-contrast --color-bar green --color-peak bright_red
```

### Profile file validation

Profile files are validated field-by-field. If a profile contains an unknown key,
an invalid marker style, or an unsupported color value, `eq-cli` reports the
specific profile field that failed validation.

### Start the equalizer with interactive device selection

```sh
eq-cli
```

Select a device from the numbered prompt that appears.

On startup, the CLI also prints the active render settings (profile, mode,
volume mode, channel mode, peak hold frames, history rows, and refresh rate).

During runtime on supported terminals (Windows, macOS, Linux), keyboard hotkeys are available:

- `f`: freeze/unfreeze the display
- `r`: reset peak markers
- `s`: save a snapshot of the current chart
- `p`: export the current effective profile settings
- `q`: quit

Runtime snapshots are written to the current working directory by default. You
can override the target directory with:

```sh
eq-cli --device <identifier-or-name> --snapshot-dir snapshots
```

The built-in `studio` profile defaults runtime snapshots to ANSI output in the
`snapshots/` directory.

Runtime profile exports are written to the current working directory as
`eq-cli-profile-001.json`, `eq-cli-profile-002.json`, and so on. Each file is a
valid profile file containing one profile named after the file stem, including
the current runtime tuning values that can be loaded back with `--profile-file`.

The shortcuts/status legend is shown on-screen by default and includes freeze
state (`ON`/`OFF`). You can hide it with:

```sh
eq-cli --device <identifier-or-name> --no-shortcuts
```

## Web UI mode

`eq-cli` includes a second UI mode that renders the spectrum in your browser
using the Web Audio API.  In this mode Python serves only a local configuration
endpoint; all audio capture and real-time FFT processing run entirely inside the
browser with no round-trip to Python.  This makes the web version faster than
the terminal renderer because it runs at the native display refresh rate
(60–144 Hz) using GPU-accelerated `<canvas>` drawing.

### Start the web UI

```sh
eq-cli --ui web
```

The server starts on `http://127.0.0.1:8080/` by default.  Open the URL in
any modern browser, click **Detect Devices** to grant microphone permission,
select an input device and click **▶ Start**.

### Open browser automatically

```sh
eq-cli --ui web --open-browser
```

### Customise host and port

```sh
eq-cli --ui web --web-host 127.0.0.1 --web-port 8888
```

The server is bound to loopback (`127.0.0.1`) by default so it is not reachable
from other machines.  The web UI is designed for single-user, localhost-only
access with no authentication.

### Use a profile with web mode

All profile and color options work the same in web mode and are forwarded to the
browser as display configuration:

```sh
eq-cli --ui web --profile studio
eq-cli --ui web --profile high-contrast --color-bar green --color-peak red
eq-cli --ui web --db-min -60 --db-max 0 --history-rows 4
```

### Browser controls

| Key / button | Action |
|---|---|
| `F` or Freeze button | Toggle freeze (hold current frame) |
| `R` or Reset Peaks button | Clear all peak markers |
| `S` or Snapshot button | Save a PNG of the current display |
| Vol dropdown | Switch between Relative and Absolute volume mode |
| Ch dropdown | Select channel (Sum / Left / Right / Mid / Side / Mono) |

> **Note:** The `side` channel mode (L−R) requires an `AudioWorklet` that is
> not yet implemented; it falls back to `sum` in the browser.  All other channel
> modes are fully supported via `ChannelSplitterNode`.

## Troubleshooting

### Tone peaks appear at the wrong frequencies (e.g. 150 Hz / 250 Hz instead of 50 Hz)

This is expected physical behaviour when routing audio through **speakers and a
microphone**, and is not a bug in the analyzer.  Two effects combine to shift the
apparent peak away from the fundamental:

1. **Speaker harmonic distortion.**  Small speakers (laptop, monitor, phone) roll
   off 20–30 dB below roughly 80 Hz.  To move enough air they work harder at
   those frequencies, producing heavy *odd-harmonic* distortion.  For a 50 Hz
   source tone the 3rd harmonic (150 Hz) and 5th harmonic (250 Hz) easily exceed
   the attenuated fundamental at the diaphragm.

2. **Microphone hardware high-pass filter.**  Most built-in laptop and headset
   microphones include a hardware HPF around 80–120 Hz that attenuates the
   fundamental by an additional 10–20 dB before the signal ever reaches the
   browser — even though all browser-side processing (`echoCancellation`,
   `noiseSuppression`, `autoGainControl`) is disabled by default.

The net result for a "50 Hz tone played on speakers → re-captured by a mic" is
typically: fundamental at around −50 dB, 3rd harmonic at around −5 dB, 5th
harmonic at around −15 dB.  That is exactly what is shown in the analyzer.

**To verify the analyzer is accurate, bypass the acoustic path entirely:**

- **Linux:** use a PulseAudio/PipeWire *monitor* source (the loopback device
  that captures the software mix rather than the microphone).
- **macOS:** install [BlackHole](https://github.com/ExistingMusicBed/BlackHole)
  or [Loopback](https://rogueamoeba.com/loopback/) and select the virtual device.
- **Windows:** enable *Stereo Mix* in Sound settings or use
  [VB-CABLE](https://vb-audio.com/Cable/).

With a digital loopback selected, a pure 50 Hz tone should produce a single
clean peak at the 50 Hz band with no energy at 150 Hz or 250 Hz, confirming
that the frequency mapping and rendering pipeline are correct.

## Platform notes

| Platform | Tested | Notes |
|----------|--------|-------|
| Windows  | Intended | Requires PortAudio via sounddevice wheel. |
| macOS    | Intended | PortAudio is bundled in the sounddevice wheel. |
| Linux    | Intended | May require `apt install libportaudio2` or equivalent. |

## Contributing

For development setup, testing, linting, and release instructions, see [DEVELOPER.md](DEVELOPER.md).
