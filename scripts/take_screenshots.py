"""
Headless screenshot generator for the LV-Gen GUI.

Launches the application with the offscreen Qt platform (no display required),
loads a sample song, and captures each panel to docs/screenshots/.

Usage (from repo root, with venv active):
    QT_QPA_PLATFORM=offscreen python scripts/take_screenshots.py

Screenshots are saved to docs/screenshots/ and committed to the repo so that
pandoc can embed them when building the HTML manual:
    pandoc docs/MANUAL.md --standalone --embed-resources -o LV-Gen-Manual.html

Captured images:
    main-window.png      — full application window
    song-selector.png    — Song Selector panel (left column)
    timeline-editor.png  — Timeline Editor panel (center bottom)
    theme-editor.png     — Theme Editor panel (right column)
    preview-panel.png    — Preview panel (center top)
"""

import os
import sys
from pathlib import Path

# Ensure the repo root is on sys.path so src.* imports work
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

OUTPUT_DIR = REPO_ROOT / "docs" / "screenshots"
SAMPLE_SONG = "careers"  # Must exist in input/audio/ and input/lyrics/

# Window dimensions used for screenshots (matches MainWindow defaults)
WINDOW_W = 1400
WINDOW_H = 900


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Force offscreen rendering — no display needed
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PyQt6.QtCore import QTimer
    from PyQt6.QtWidgets import QApplication

    from src.core.song_resolver import resolve_song
    from src.gui.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("Lyric Video Generator")
    app.setStyleSheet("""
        QGroupBox {
            font-size: 14pt;
            font-weight: 600;
            margin-top: 26px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            left: 10px;
            top: 4px;
            padding: 0 4px;
        }
    """)

    window = MainWindow()
    window.resize(WINDOW_W, WINDOW_H)
    window.show()

    # Load a sample song so panels are populated
    try:
        paths = resolve_song(SAMPLE_SONG)
        str_paths = {k: str(v) if v else None for k, v in paths.items()}
        window._on_song_loaded(str_paths)
        print(f"Loaded sample song: {SAMPLE_SONG!r}")
    except Exception as e:
        print(f"Warning: could not load sample song {SAMPLE_SONG!r}: {e}")
        print("Screenshots will show the empty initial state.")

    # Process pending events so the UI is fully rendered before grabbing
    def capture():
        try:
            _capture_all(window)
        finally:
            app.quit()

    QTimer.singleShot(200, capture)
    app.exec()


def _save(widget, filename: str) -> None:
    path = OUTPUT_DIR / filename
    pixmap = widget.grab()
    if pixmap.save(str(path)):
        print(f"  Saved: {path.relative_to(REPO_ROOT)}")
    else:
        print(f"  ERROR: Failed to save {path}")


def _capture_all(window) -> None:
    print(f"\nCapturing screenshots to {OUTPUT_DIR.relative_to(REPO_ROOT)}/")

    # Full window
    _save(window, "main-window.png")

    # Individual panels (accessed via private attributes set in MainWindow.__init__)
    panels = {
        "song-selector.png": "_song_selector",
        "timeline-editor.png": "_timeline",
        "theme-editor.png": "_theme_editor",
        "preview-panel.png": "_preview",
    }
    for filename, attr in panels.items():
        panel = getattr(window, attr, None)
        if panel is not None:
            _save(panel, filename)
        else:
            print(f"  Skipped {filename}: attribute {attr!r} not found on MainWindow")

    print("\nDone.")


if __name__ == "__main__":
    main()
