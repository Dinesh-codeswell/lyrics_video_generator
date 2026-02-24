# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Python CLI and PyQt6 desktop GUI that generates YouTube-ready 1080p lyric videos from a JSON lyrics file and audio track, with configurable text animations and themes. Output is MP4 (libx264/AAC).

## Commands

```bash
# Setup
python3 -m venv venv && source venv/bin/activate
pip install -e .

# Run via CLI entry point (auto-match from input/ folders)
lyric-video --song disciples-of-dysfunction

# Run with explicit paths
lyric-video --lyrics input/lyrics/disciples-of-dysfunction.json --audio input/audio/disciples-of-dysfunction.mp3

# Run directly
python -m src.cli.main --song disciples-of-dysfunction

# CLI options
lyric-video --song NAME | --lyrics FILE --audio FILE [--background FILE] [--no-background] [--theme FILE] [--lyric-position left|center|right] [--highlight-mode line|word|character] [--text-overlay 0-100] [--output PATH] [--fps 30] [--preview]
```

FFmpeg must be installed on the system (required by moviepy).

No test suite or linting is currently configured.

## Architecture

**Pipeline flow:** CLI (`src/cli/main.py`) → `generate_video()` (`src/core/video_generator.py`) → on-demand frame rendering via moviepy's `VideoClip(make_frame)`.

**Core modules** (`src/core/`):
- `video_generator.py` — Main pipeline. Builds frames on-demand with per-line caching (only current line's frames in memory). The `make_frame(t)` closure maps time → lyric line → animation frame.
- `lyrics_parser.py` — Parses lyrics JSON into `LyricLine` dataclass (`text`, `start_time`, `end_time`, `duration`). Empty text `""` marks the end.
- `text_renderer.py` — PIL-based rendering at 1920x1080. Handles font loading (with fallback chain), hex colors, shadows, text alpha blending.
- `audio_handler.py` — Loads audio via moviepy `AudioFileClip`.
- `theme_loader.py` — Loads theme JSON merged with hardcoded defaults.
- `song_resolver.py` — Auto-matches song files from `input/` directories by name. Resolves lyrics, audio, and background paths.

**Animation system** (`src/animations/`):
- `scroll.py` — `ScrollingAnimation`. Continuous scrolling view; active line centered, adjacent lines visible at decreasing opacity. Smooth eased transitions between lines.

**GUI** (`src/gui/`):
- `main.py` — Entry point for `lyric-video-gui`. Launches the PyQt6 `MainWindow`.
- `main_window.py` — Top-level window. Owns all panels, wires cross-panel signals, manages dirty-state tracking (lyrics + theme), window title indicator, `closeEvent` prompt, and keyboard shortcuts (⌘S/⌘⇧S/⌘Z/⌘⇧Z/Space).
- `panels/song_selector.py` — Scans `input/` folders, lists songs with file-presence indicators, emits `song_loaded(dict)` on selection.
- `panels/timeline_editor.py` — Visual timeline with draggable markers. Uses `QUndoStack` + command pattern (`_MoveMarkerCommand`, `_EditTextCommand`) for undo/redo. Emits `lyrics_modified` when dirty.
- `panels/theme_editor.py` — Collapsible-section controls for all theme properties. Emits `theme_changed(Theme)` on every edit; `theme_dirty_changed(bool)` for save-state tracking.
- `panels/preview_panel.py` — Renders a preview clip on a `QThread` worker, plays it back via `QVideoWidget`/`QMediaPlayer`. Shows a stale indicator (⚠) when theme or lyrics change after the last render.
- `panels/export_bar.py` — Export settings (filename, dir, FPS), progress bar, cancel support via `threading.Event`. Calls a `pre_export_check` callback (set by `MainWindow`) before starting.

**Data formats:**
- Lyrics: JSON with `title`, `artist`, `lyrics[]` (each entry has `time` in seconds and `text`). See `input/lyrics/disciples-of-dysfunction.json`.
- Themes: JSON with properties for colors, fonts, layout, highlighting, and overlay. See `themes/durt_nurs.json` and the README for the full schema.

## Key Conventions

- moviepy v2.0+ API: use `with_fps()`, `with_audio()`, `VideoClip(frame_function)` — not the deprecated v1 methods.
- Python 3.10+ required. Dependencies: moviepy, Pillow, click, numpy, PyQt6.
- Preview mode renders first 30 seconds only.
- Input directories are `input/audio/`, `input/lyrics/`, `input/backgrounds/` (contents gitignored, structure kept via `.gitkeep`).
- Output directory is `output/` (gitignored).
