# Lyric Video Generator — User Guide

> Live reference document. Update as features are added or changed.

---

## Launching the App

**macOS app (downloaded release):**

Double-click **LV-Gen** in your Applications folder. On first launch, right-click → **Open** if macOS blocks it.

**From source:**

```bash
# Activate the virtual environment (required each new terminal session)
source venv/bin/activate

# Launch the GUI
lyric-video-gui

# Launch the CLI (headless render)
lyric-video --song <name>
```

---

## Input Files

Place files in the matching `input/` subdirectory. The song name must match across all three folders for auto-detection to work.

| Type       | Folder                  | Formats             |
|------------|-------------------------|---------------------|
| Audio      | `input/audio/`          | `.mp3`, `.wav`, `.flac` |
| Lyrics     | `input/lyrics/`         | `.json`             |
| Background | `input/backgrounds/`    | `.jpg`, `.png`, `.mp4` |

---

## Lyrics JSON Format

```json
{
  "title": "Song Title",
  "artist": "Artist Name",
  "lyrics": [
    { "time": 10.5,  "text": "First lyric line" },
    { "time": 14.2,  "text": "Second lyric line" },
    { "time": 18.0,  "text": "Third lyric line" },
    { "time": 22.0,  "text": "" }
  ]
}
```

**Rules:**
- `time` — seconds from the start of the audio when this line appears
- `text` — the lyric line to display
- The **final entry must have `"text": ""`** — this is the end marker that defines when the last line stops displaying
- Each line's display duration = next entry's `time` minus this entry's `time`
- Gaps between lines (instrumentals) are created by spacing timestamps far apart — the screen is blank during the gap
- Starting all `time` values at `0` is valid; use the Timeline Editor to stamp them

---

## GUI Overview

The window has five panels:

| Panel | Location | Purpose |
|-------|----------|---------|
| Song Selector | Left column | Lists detected songs; click to load |
| Preview | Center top | Renders and plays back a preview clip |
| Timeline Editor | Center bottom | Visual timestamping and lyric editing |
| Theme Editor | Right column | All visual style controls |
| Transport + Export | Bottom bar | Playback controls and video export |

---

## Song Selector

- Lists all songs detected in `input/` folders
- Shows icons indicating which files are present (audio, lyrics, background)
- **Click a song to load it** into all panels
- If you have unsaved lyric changes, a dialog prompts to Save / Discard / Cancel before loading

### Import Song Dialog

**File → Import Song** (or the Import button in the Song Selector) opens the Import Song dialog, which lets you create a new song's lyrics file without leaving the app:

1. Paste raw lyric text into the text area (one line per entry)
2. Enter the song title and artist name
3. Click **Import** — the `.json` lyrics file is written to `input/lyrics/` with all timestamps set to `0`
4. The new song appears in the Song Selector and is ready for timestamping in the Timeline Editor

---

## Timeline Editor

### Visual Elements

| Element | Appearance | Meaning |
|---------|-----------|---------|
| Ruler | Top strip | Time in M:SS |
| Blue triangle + line | Normal marker | Unselected lyric line |
| Yellow triangle + line | Highlighted marker | Currently selected |
| Green triangle + line | Active marker | Line playing right now |
| Red vertical line | Cursor | Current playback position |

### Toolbar Controls

| Control | Function |
|---------|----------|
| Zoom slider | Expand/compress the timeline horizontally |
| Ctrl + scroll | Zoom in/out with the mouse wheel |
| Snap 0.1s | Snaps dragged markers to 0.1s grid (uncheck for free movement) |
| + Insert | Insert a new blank marker after the selected one |
| − Delete | Delete the selected marker |

### Marker Detail Strip (bottom of panel)

Shows the selected marker's data. Fields are editable:

| Field | Description |
|-------|-------------|
| ◀ Prev / Next ▶ | Navigate to adjacent markers |
| Text field | Edit the lyric line text |
| Start: | Exact start time in seconds (editable via spinner) |
| End: | Calculated end time (read-only) |
| Dur: | Calculated duration (read-only) |
| Save button | Save all changes to disk |

---

## Tap-to-Stamp Workflow

The intended workflow for timestamping a new song from scratch (all times = 0):

1. Load the song — all markers pile up at the left edge (time 0), which is expected
2. Press **Space** to start playback
3. Press **Enter** each time you hear a lyric line begin
   - First tap auto-selects marker 0 if nothing is selected
   - Each tap stamps the current marker to the playback position, then advances to the next
4. Press **Space** to pause at any time
5. Press **⌘S** when done to save timestamps to the JSON file

### Recovering from Misqueues

- **⌘Z** to undo the last stamp — the stamp cursor moves back to that marker
- Click anywhere on the timeline to seek the audio back to the right spot
  (this deselects the marker but the stamp cursor remembers where you are)
- Press **Enter** to resume stamping from where you undid — the stamp cursor
  holds position independently of the visual selection

### Nuances

- Clicking **empty space** on the timeline seeks the audio but clears the visual selection — this is safe; the stamp cursor is not affected
- Clicking a **marker triangle** selects it and sets the stamp cursor to that index — pressing Enter will stamp that specific marker
- The stamp cursor only resets to 0 when a new song is loaded

---

## Inserting and Deleting Markers

### Insert After Selected

1. Click the marker you want to insert after (it turns yellow)
2. Click **+ Insert** in the toolbar
3. A new blank marker appears at the midpoint between the selected marker and the next one
4. Type the lyric text in the detail strip's text field
5. Drag the marker or adjust the **Start:** spinner to set the correct time
6. Save with **⌘S**

### Delete Selected

1. Click the marker to select it
2. Click **− Delete**
3. The marker is removed; the adjacent marker is selected
4. Both Insert and Delete are fully undoable with **⌘Z**

### Known Limitation

Insert and Delete use fixed list indices in the undo stack. If you insert/delete a marker and then try to undo an earlier *move* command (from before the insert/delete), that undo may operate on the wrong marker. Treat insert/delete as final corrections — do not mix them with undoing earlier stamps.

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| **Space** | Play / Pause audio |
| **Enter** | Stamp selected marker to current playback position, advance to next |
| **⌘Z** | Undo last action (move, text edit, insert, delete) |
| **⌘⇧Z** | Redo |
| **⌘S** | Save lyrics to JSON |
| **⌘⇧S** | Save theme |

> Space and Enter are blocked when a text field or spinner has focus, so typing in the detail strip won't accidentally trigger playback or stamping.

---

## Theme Editor

Controls the visual style of the video. Changes are reflected in the Preview panel (which shows a ⚠ stale indicator until re-rendered).

### Theme Properties Reference

| Property | Type | Description |
|----------|------|-------------|
| `name` | string | Theme identifier |
| `background_color` | `#RRGGBB` | Canvas background colour |
| `text_color` | `#RRGGBB` | Default lyric text colour |
| `active_text_color` | `#RRGGBB` or null | Colour of the currently playing line (null = same as `text_color`) |
| `active_text_bold` | bool | Bold the active line |
| `active_text_glow` | bool | Glow effect on active line |
| `active_glow_color` | `#RRGGBB` or null | Glow colour (null = same as `active_text_color`) |
| `inactive_text_opacity_gradient` | list of floats 0–1 | Opacity of lines above/below active; e.g. `[0.6, 0.4, 0.2]` |
| `font_family` | string | Font name with fallback chain |
| `font_size` | int | Base font size in pixels |
| `line_spacing` | float | Line height multiplier (e.g. `1.5` = 1.5 × font_size) |
| `lyric_position` | `left` / `center` / `right` | Horizontal text alignment |
| `highlight_mode` | `line` / `word` / `character` | What unit gets highlighted |
| `highlight_dim_alpha` | float 0–1 | Opacity of non-highlighted text within an active line |
| `text_overlay_opacity` | int 0–100 | Opacity of a solid colour overlay behind text |
| `text_overlay_color` | `#RRGGBB` | Colour of the text overlay |

### Saving Themes

- **⌘⇧S** saves the currently loaded theme file
- **File → Save Theme** is the menu equivalent
- **File → Open Theme…** loads a theme JSON from `themes/`
- Theme files live in `themes/` — copy `themes/default.json` as a starting point

---

## Preview Panel

- Click **Render Preview** to generate a preview clip (renders first 30 seconds)
- A **⚠ stale** indicator appears when lyrics or theme have changed since the last render
- Playback uses the same transport controls as the audio player

---

## Export (Transport Bar)

| Control | Description |
|---------|-------------|
| Filename field | Output file name (without path) |
| Output directory | Defaults to `output/`; click the folder button to change |
| FPS | 24, 30, or 60 frames per second |
| Export button | Starts the full render |
| Progress bar | Shows frame-by-frame progress |
| Cancel button | Cancels mid-render cleanly |

- If you have unsaved lyrics or theme changes, a dialog prompts before export starts
- Output is always 1920×1080 MP4 (H.264 video + AAC audio)
- Rendered files go to `output/` (gitignored)

---

## CLI Reference

```bash
# Auto-match by song name
lyric-video --song my-song

# Explicit file paths
lyric-video --lyrics input/lyrics/my-song.json --audio input/audio/my-song.mp3

# All options
lyric-video \
  --song NAME \
  --lyrics FILE \
  --audio FILE \
  [--background FILE] \
  [--no-background] \
  [--theme FILE] \
  [--lyric-position left|center|right] \
  [--highlight-mode line|word|character] \
  [--text-overlay 0-100] \
  [--output PATH] \
  [--fps 30] \
  [--preview]      # renders first 30 seconds only
```

> FFmpeg must be installed on the system (required by moviepy).

---

## File Structure

```
input/
  audio/          # .mp3 / .wav / .flac source files
  lyrics/         # .json lyrics files
  backgrounds/    # .jpg / .png / .mp4 background files
output/           # rendered videos (gitignored)
themes/           # .json theme files
src/
  cli/            # CLI entry point
  core/           # video pipeline, parser, renderer, theme loader
  animations/     # scrolling animation
  gui/            # PyQt6 desktop app
    panels/       # individual UI panels
```
