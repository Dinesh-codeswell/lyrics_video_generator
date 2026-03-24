# Changelog

All notable changes to LV-Gen are documented here.

---

## [0.1.1] — 2026-03-24

### Added
- Import Song dialog — create a new song's lyrics file directly from pasted text without leaving the app
- Title bar icon on macOS
- User manual (`docs/MANUAL.md`) with 15 sections covering installation, all GUI panels, tap-to-stamp workflow, theme editor, CLI reference, keyboard shortcuts, and troubleshooting
- Headless screenshot generator (`scripts/take_screenshots.py`) using `QT_QPA_PLATFORM=offscreen` — all GUI panel screenshots committed to `docs/screenshots/`
- Automated HTML manual build in the release workflow — `LV-Gen-Manual-vX.X.X.html` now attached to each GitHub Release alongside the `.dmg`
- Code signing and notarization — releases are now signed with a Developer ID certificate and notarized by Apple; no Gatekeeper warning on launch
- New-user onboarding improvements

### Changed
- Removed Durt Nurs branding; app is now generic
- Build configs (`build.spec`, `setup_py2app.py`) now read version dynamically from `pyproject.toml` via `importlib.metadata` — no more hardcoded version strings

### Fixed
- Version mismatch between `pyproject.toml`, `build.spec`, and `setup_py2app.py`
- App crash on launch due to missing `imageio` package metadata in PyInstaller bundle (`importlib.metadata.version()` now resolved via `copy_metadata`)

---

## [0.1.0] — 2025-01-01

Initial release.

### Added
- CLI (`lyric-video`) for headless video generation
- GUI (`lyric-video-gui`) with Song Selector, Timeline Editor, Theme Editor, Preview Panel, and Export bar
- Tap-to-Stamp workflow for real-time lyric timestamping
- Draggable timeline markers with undo/redo (`QUndoStack`)
- Theme system with JSON configuration (colors, fonts, layout, highlighting, text overlay, shadows)
- Highlight modes: `line`, `word`, `character`
- Continuous scrolling animation with opacity gradient for inactive lines
- Embedded preview player (renders first 30 seconds)
- macOS `.dmg` release via GitHub Actions (PyInstaller)
