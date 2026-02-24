# Lyric Video Generator

Generate lyric videos with timed text animations from a JSON lyrics file and an audio track. Outputs YouTube-ready 1080p MP4 videos (H.264 video, AAC audio).

## Requirements

- Python 3.10+
- FFmpeg (required by moviepy for video encoding)

## Setup

```bash
# Clone the repo
git clone https://github.com/CuWilliams/lyric-video-generator.git
cd lyric-video-generator

# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate

# Install as an editable package (installs deps + registers the lyric-video command)
pip install -e .
```

> **Note:** On macOS, use `pip3` instead of `pip` if you are not in a virtual environment.

### FFmpeg

moviepy requires FFmpeg to be installed on your system:

- **macOS:** `brew install ffmpeg`
- **Ubuntu/Debian:** `sudo apt install ffmpeg`
- **Windows:** Download from https://ffmpeg.org/download.html and add to PATH

## Usage

Place your files in the `input/` folders:
- `input/audio/` — MP3/WAV song files
- `input/lyrics/` — lyrics JSON files
- `input/backgrounds/` — looping MP4 background videos (optional)

Then run with `--song` to auto-match by filename:

```bash
lyric-video --song disciples-of-dysfunction
```

Or use explicit paths:

```bash
lyric-video --lyrics input/lyrics/disciples-of-dysfunction.json \
            --audio input/audio/disciples-of-dysfunction.mp3 \
            --theme themes/durt_nurs.json \
            --output output/video.mp4
```

### GUI

A desktop GUI is also available:

```bash
lyric-video-gui
```

The GUI provides a song browser, visual timeline editor with draggable markers, live theme editor, embedded preview player, and export controls — all backed by the same rendering engine as the CLI.

### Options

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `--song` | * | — | Song name to auto-match from `input/` folders |
| `--lyrics` | * | — | Path to lyrics JSON file |
| `--audio` | * | — | Path to audio file (mp3, wav, etc.) |
| `--background` | No | auto-matched | Path to background video |
| `--no-background` | No | off | Force solid color background |
| `--theme` | No | `themes/durt_nurs.json` | Path to theme JSON |
| `--lyric-position` | No | theme default | Text alignment: `left`, `center`, or `right` (overrides theme) |
| `--highlight-mode` | No | theme default | Active line style: `line`, `word`, or `character` (overrides theme) |
| `--text-overlay` | No | `0` | Opacity (0–100) of semi-transparent strip behind lyrics |
| `--output` | No | `output/<title>.mp4` | Output file path |
| `--fps` | No | `30` | Frame rate |
| `--preview` | No | off | Generate only first 30 seconds |

\* Provide either `--song` or both `--lyrics` and `--audio`.

### Examples

```bash
# Auto-match mode (looks in input/ folders)
lyric-video --song disciples-of-dysfunction

# Quick preview with auto-match (first 30 seconds)
lyric-video --song disciples-of-dysfunction --preview

# Explicit paths
lyric-video --lyrics input/lyrics/disciples-of-dysfunction.json \
            --audio input/audio/disciples-of-dysfunction.mp3

# Custom output path and theme
lyric-video --lyrics my_lyrics.json --audio my_song.wav \
            --theme my_theme.json --output my_video.mp4

# Override background for a song
lyric-video --song disciples-of-dysfunction --background /path/to/custom_bg.mp4

# Override style flags (all override the active theme)
lyric-video --song disciples-of-dysfunction --lyric-position left --highlight-mode word
```

You can also run the CLI directly without installing the package:

```bash
python -m src.cli.main --song disciples-of-dysfunction
```

### Notes

- The `--preview` flag is useful for quickly testing your lyrics/theme before generating a full-length video.
- Generated videos are saved to the `output/` directory by default. This directory is gitignored.
- If lyrics start after 0:00 (e.g. an instrumental intro), the video will show a blank background until the first lyric line.

## Lyrics Format

```json
{
  "title": "Song Title",
  "artist": "Artist Name",
  "lyrics": [
    { "time": 21.53, "text": "First line of lyrics" },
    { "time": 25.01, "text": "Second line" },
    { "time": 30.00, "text": "" }
  ]
}
```

- `time` — when the line appears, in seconds (float)
- `text` — the lyric text to display
- An empty `text` field marks the end of lyrics (used for timing the final line)

See `input/lyrics/disciples-of-dysfunction.json` for a complete example.

## Animation

Lyric lines scroll continuously — the active line is centered on screen and adjacent lines are visible above and below at decreasing opacity (controlled by `inactive_text_opacity_gradient` in the theme). Transitions between lines are smoothly eased.

Active-line highlighting is set via `highlight_mode` in the theme or `--highlight-mode` on the CLI:

- **line** — the entire active line is rendered at full opacity in `active_text_color` (default)
- **word** — words are highlighted progressively as the line plays
- **character** — characters are highlighted progressively as the line plays

## Themes

Themes are JSON files that control the visual style. The default theme is `themes/durt_nurs.json`:

```json
{
  "name": "Durt Nurs",
  "background_color": "#1a1a1a",
  "text_color": "#ffffff",
  "active_text_color": "#ffcc00",
  "active_text_bold": true,
  "active_text_glow": true,
  "active_glow_color": "#ffcc00",
  "inactive_text_opacity_gradient": [0.6, 0.4, 0.2],
  "font_family": "Arial Bold",
  "font_size": 72,
  "line_spacing": 1.5,
  "lyric_position": "center",
  "highlight_mode": "line",
  "text_overlay_opacity": 0,
  "text_overlay_color": "#000000"
}
```

### Theme Properties

**Colors**

| Property | Description | Default |
|----------|-------------|---------|
| `background_color` | Solid background color (hex `#RRGGBB`) | `#1a1a1a` |
| `text_color` | Color of inactive lyric lines | `#ffffff` |
| `active_text_color` | Color of the currently active line. `null` falls back to `text_color` | `null` |
| `active_glow_color` | Color of the soft glow on the active line. `null` falls back to `active_text_color` | `null` |
| `text_shadow_color` | Hex color of the text drop shadow | `#000000` |

**Active Line**

| Property | Description | Default |
|----------|-------------|---------|
| `active_text_bold` | Render the active line in a bold font variant | `false` |
| `active_text_glow` | Enable a soft glow halo around the active line | `true` |

**Inactive Lines**

| Property | Description | Default |
|----------|-------------|---------|
| `inactive_text_opacity_gradient` | Array of opacities for lines 1, 2, 3 positions away from the active line | `[0.6, 0.4, 0.2]` |

**Font & Layout**

| Property | Description | Default |
|----------|-------------|---------|
| `font_family` | Font name or path (falls back through common system fonts) | `Arial` |
| `font_size` | Base font size in pixels | `72` |
| `line_spacing` | Line height as a multiplier of `font_size` (e.g. `1.5` = 1.5× font size) | `1.5` |
| `lyric_position` | Horizontal text alignment: `left`, `center`, or `right` | `center` |

**Highlighting**

| Property | Description | Default |
|----------|-------------|---------|
| `highlight_mode` | How the active line is highlighted: `line` (full line), `word`, or `character` | `line` |
| `highlight_dim_alpha` | Opacity of un-highlighted tokens in `word`/`character` mode (0.0–1.0) | `0.3` |

**Text Overlay**

| Property | Description | Default |
|----------|-------------|---------|
| `text_overlay_opacity` | Opacity (0–100) of the semi-transparent strip behind the lyrics column | `0` |
| `text_overlay_color` | Hex color of the overlay | `#000000` |

**Text Shadow**

| Property | Description | Default |
|----------|-------------|---------|
| `text_shadow` | Enable a drop shadow on all text | `false` |
| `text_shadow_color` | Hex color of the shadow | `#000000` |
| `text_shadow_offset` | Shadow offset as `[x, y]` pixels | `[3, 3]` |

## Project Structure

```
lyric-video-generator/
├── src/
│   ├── core/
│   │   ├── lyrics_parser.py      # lyrics JSON parsing and validation
│   │   ├── text_renderer.py      # text/font rendering with Pillow
│   │   ├── video_generator.py    # main video generation pipeline
│   │   ├── audio_handler.py      # audio file loading
│   │   ├── theme_loader.py       # theme JSON loading with defaults
│   │   └── song_resolver.py      # auto-match song files from input/
│   ├── animations/
│   │   └── scroll.py             # continuous scrolling animation
│   ├── cli/
│   │   └── main.py               # CLI entry point (lyric-video)
│   └── gui/
│       ├── main.py               # GUI entry point (lyric-video-gui)
│       ├── main_window.py        # main application window
│       └── panels/
│           ├── song_selector.py  # song browser sidebar
│           ├── timeline_editor.py # visual timeline with draggable markers
│           ├── theme_editor.py   # theme property controls
│           ├── preview_panel.py  # embedded video preview
│           └── export_bar.py     # export settings and progress
├── input/
│   ├── audio/                    # MP3/WAV song files (gitignored)
│   ├── lyrics/                   # lyrics JSON files (gitignored)
│   └── backgrounds/              # looping MP4 backgrounds (gitignored)
├── themes/
│   └── durt_nurs.json            # default theme
├── output/                       # generated videos (gitignored)
├── requirements.txt
└── pyproject.toml
```
