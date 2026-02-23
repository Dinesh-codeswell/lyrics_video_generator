"""Export controls bar — output settings, progress, and cancel."""

from __future__ import annotations

import subprocess
import sys
import threading
from pathlib import Path
from typing import Callable

from PyQt6.QtCore import QObject, QThread, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.core.theme_loader import Theme, load_theme
from src.core.video_generator import RenderCancelled, generate_video

_DEFAULT_OUTPUT_DIR = "output"
_FPS_OPTIONS = ["24", "30", "60"]
_DEFAULT_FPS = "30"


# ──────────────────────────────────────────────────────────────────────────────
# Worker
# ──────────────────────────────────────────────────────────────────────────────

class _ExportWorker(QObject):
    """Calls generate_video() on a background thread."""

    progress  = pyqtSignal(int, int)  # current_frame, total_frames
    finished  = pyqtSignal(str)       # output path
    error     = pyqtSignal(str)       # error message
    cancelled = pyqtSignal()

    def __init__(
        self,
        song_paths: dict,
        theme: Theme,
        fps: int,
        output_path: str,
    ) -> None:
        super().__init__()
        self._song_paths = song_paths
        self._theme = theme
        self._fps = fps
        self._output_path = output_path
        self._cancel_event = threading.Event()

    def cancel(self) -> None:
        self._cancel_event.set()

    def run(self) -> None:
        out = Path(self._output_path)
        try:
            generate_video(
                lyrics_path=self._song_paths["lyrics"],
                audio_path=self._song_paths["audio"],
                output_path=out,
                theme=self._theme,
                fps=self._fps,
                background_path=self._song_paths.get("background"),
                logger=None,
                progress_callback=lambda c, t: self.progress.emit(c, t),
                cancel_event=self._cancel_event,
            )
            self.finished.emit(str(out))
        except RenderCancelled:
            # Clean up incomplete file
            if out.exists():
                try:
                    out.unlink()
                except OSError:
                    pass
            self.cancelled.emit()
        except Exception as exc:  # noqa: BLE001
            self.error.emit(str(exc))


# ──────────────────────────────────────────────────────────────────────────────
# ExportBar
# ──────────────────────────────────────────────────────────────────────────────

class ExportBar(QWidget):
    """Bottom bar: output settings, export button, and live progress."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._song_paths: dict | None = None
        self._theme: Theme = load_theme()
        self._thread: QThread | None = None
        self._worker: _ExportWorker | None = None
        self._pre_export_check: Callable[[], bool] | None = None
        self._build_ui()

    # ──────────────────────────────────────────────────────────────────
    # Public slots
    # ──────────────────────────────────────────────────────────────────

    def song_loaded(self, paths: dict) -> None:
        """Called when a new song is selected."""
        self._song_paths = paths
        # Auto-populate filename from audio stem
        audio = paths.get("audio")
        if audio:
            self._filename_edit.setText(Path(audio).stem + ".mp4")
        self._export_btn.setEnabled(True)
        self._update_status("Ready")

    def set_pre_export_check(self, fn: Callable[[], bool]) -> None:
        """Register a callback called before export starts; return False to abort."""
        self._pre_export_check = fn

    def on_theme_changed(self, theme: Theme) -> None:
        self._theme = theme

    # ──────────────────────────────────────────────────────────────────
    # UI
    # ──────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 4, 8, 2)
        outer.setSpacing(2)

        # ── Row 1: settings + buttons ──────────────────────────────
        row1 = QHBoxLayout()
        row1.setSpacing(6)

        row1.addWidget(QLabel("File:"))
        self._filename_edit = QLineEdit("untitled.mp4")
        self._filename_edit.setFixedWidth(200)
        row1.addWidget(self._filename_edit)

        row1.addWidget(QLabel("Dir:"))
        self._dir_edit = QLineEdit(_DEFAULT_OUTPUT_DIR)
        self._dir_edit.setFixedWidth(140)
        row1.addWidget(self._dir_edit)

        browse_btn = QPushButton("…")
        browse_btn.setFixedWidth(28)
        browse_btn.setToolTip("Browse output directory")
        browse_btn.clicked.connect(self._on_browse)
        row1.addWidget(browse_btn)

        row1.addWidget(QLabel("FPS:"))
        self._fps_combo = QComboBox()
        self._fps_combo.addItems(_FPS_OPTIONS)
        self._fps_combo.setCurrentText(_DEFAULT_FPS)
        self._fps_combo.setFixedWidth(56)
        row1.addWidget(self._fps_combo)

        res_label = QLabel("1920×1080")
        res_label.setStyleSheet("color: gray;")
        row1.addWidget(res_label)

        row1.addStretch()

        self._export_btn = QPushButton("Export Video")
        self._export_btn.setEnabled(False)
        self._export_btn.setFixedWidth(110)
        self._export_btn.clicked.connect(self._on_export_clicked)
        row1.addWidget(self._export_btn)

        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setFixedWidth(64)
        self._cancel_btn.hide()
        self._cancel_btn.clicked.connect(self._on_cancel_clicked)
        row1.addWidget(self._cancel_btn)

        outer.addLayout(row1)

        # ── Row 2: progress + status ───────────────────────────────
        row2 = QHBoxLayout()
        row2.setSpacing(6)

        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setFixedHeight(10)
        row2.addWidget(self._progress_bar, stretch=1)

        self._status_label = QLabel("Load a song to export.")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._status_label.setStyleSheet("color: gray; font-size: 11px;")
        self._status_label.setFixedWidth(260)
        row2.addWidget(self._status_label)

        outer.addLayout(row2)

    # ──────────────────────────────────────────────────────────────────
    # Export flow
    # ──────────────────────────────────────────────────────────────────

    def _on_browse(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "Output Directory", self._dir_edit.text())
        if d:
            self._dir_edit.setText(d)

    def _on_export_clicked(self) -> None:
        if not self._song_paths or not self._song_paths.get("lyrics") or not self._song_paths.get("audio"):
            QMessageBox.warning(self, "Missing Files", "No song loaded.")
            return

        output_path = Path(self._dir_edit.text()) / self._filename_edit.text()

        if output_path.exists():
            ans = QMessageBox.question(
                self,
                "Overwrite?",
                f"{output_path.name} already exists. Overwrite?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if ans != QMessageBox.StandardButton.Yes:
                return

        if self._pre_export_check is not None and not self._pre_export_check():
            return

        fps = int(self._fps_combo.currentText())

        self._export_btn.setEnabled(False)
        self._cancel_btn.show()
        self._progress_bar.setValue(0)
        self._update_status("Starting…")

        self._thread = QThread(self)
        self._worker = _ExportWorker(
            song_paths=self._song_paths,
            theme=self._theme,
            fps=fps,
            output_path=str(output_path),
        )
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.cancelled.connect(self._on_cancelled)
        self._worker.finished.connect(self._thread.quit)
        self._worker.error.connect(self._thread.quit)
        self._worker.cancelled.connect(self._thread.quit)
        self._thread.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.finished.connect(self._on_thread_done)
        self._thread.start()

    def _on_cancel_clicked(self) -> None:
        if self._worker is not None:
            self._worker.cancel()
        self._cancel_btn.setEnabled(False)
        self._update_status("Cancelling…")

    def _on_thread_done(self) -> None:
        self._thread = None
        self._worker = None

    # ──────────────────────────────────────────────────────────────────
    # Worker callbacks
    # ──────────────────────────────────────────────────────────────────

    def _on_progress(self, current: int, total: int) -> None:
        pct = int(current * 100 / total) if total > 0 else 0
        self._progress_bar.setValue(pct)
        self._update_status(f"Rendering frame {current} of {total} ({pct}%)")

    def _on_finished(self, path: str) -> None:
        self._progress_bar.setValue(100)
        self._cancel_btn.hide()
        self._cancel_btn.setEnabled(True)
        self._export_btn.setEnabled(True)
        self._update_status(f"Done — {Path(path).name}")

        msg = QMessageBox(self)
        msg.setWindowTitle("Export Complete")
        msg.setText(f"Video saved to:\n{path}")
        open_btn = msg.addButton("Open File", QMessageBox.ButtonRole.AcceptRole)
        reveal_btn = msg.addButton("Show in Finder" if sys.platform == "darwin" else "Show in Explorer",
                                   QMessageBox.ButtonRole.ActionRole)
        msg.addButton(QMessageBox.StandardButton.Ok)
        msg.exec()

        clicked = msg.clickedButton()
        if clicked is open_btn:
            _open_path(path)
        elif clicked is reveal_btn:
            _reveal_path(path)

    def _on_error(self, msg: str) -> None:
        self._cancel_btn.hide()
        self._cancel_btn.setEnabled(True)
        self._export_btn.setEnabled(True)
        self._progress_bar.setValue(0)
        self._update_status("Export failed.")
        QMessageBox.critical(self, "Export Error", f"Export failed:\n{msg}")

    def _on_cancelled(self) -> None:
        self._cancel_btn.hide()
        self._cancel_btn.setEnabled(True)
        self._export_btn.setEnabled(True)
        self._progress_bar.setValue(0)
        self._update_status("Cancelled.")

    # ──────────────────────────────────────────────────────────────────

    def _update_status(self, text: str) -> None:
        self._status_label.setText(text)


# ──────────────────────────────────────────────────────────────────────────────
# Platform helpers
# ──────────────────────────────────────────────────────────────────────────────

def _open_path(path: str) -> None:
    if sys.platform == "darwin":
        subprocess.run(["open", path], check=False)
    elif sys.platform == "win32":
        subprocess.run(["start", "", path], shell=True, check=False)
    else:
        subprocess.run(["xdg-open", path], check=False)


def _reveal_path(path: str) -> None:
    if sys.platform == "darwin":
        subprocess.run(["open", "-R", path], check=False)
    elif sys.platform == "win32":
        subprocess.run(["explorer", "/select,", path], check=False)
    else:
        subprocess.run(["xdg-open", str(Path(path).parent)], check=False)
