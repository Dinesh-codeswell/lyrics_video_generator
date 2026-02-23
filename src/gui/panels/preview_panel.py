"""Preview panel — renders and plays back a 30-second preview clip."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from PyQt6.QtCore import QObject, QThread, Qt, pyqtSignal
from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtWidgets import (
    QDoubleSpinBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.core.theme_loader import Theme, load_theme
from src.core.video_generator import generate_video


# ──────────────────────────────────────────────────────────────────────────────
# Worker
# ──────────────────────────────────────────────────────────────────────────────

class _PreviewWorker(QObject):
    """Calls generate_video() on a background thread."""

    finished = pyqtSignal(str)  # path to rendered MP4
    error = pyqtSignal(str)     # error message string

    def __init__(
        self,
        lyrics_path: str,
        audio_path: str,
        background_path: str | None,
        theme: Theme,
        start_time: float,
        out_path: str,
    ) -> None:
        super().__init__()
        self._lyrics_path = lyrics_path
        self._audio_path = audio_path
        self._background_path = background_path
        self._theme = theme
        self._start_time = start_time
        self._out_path = out_path

    def run(self) -> None:
        try:
            generate_video(
                lyrics_path=self._lyrics_path,
                audio_path=self._audio_path,
                output_path=self._out_path,
                theme=self._theme,
                preview=True,
                preview_start=self._start_time,
                background_path=self._background_path,
                logger=None,
            )
            self.finished.emit(self._out_path)
        except Exception as exc:  # noqa: BLE001
            self.error.emit(str(exc))


# ──────────────────────────────────────────────────────────────────────────────
# Panel
# ──────────────────────────────────────────────────────────────────────────────

class PreviewPanel(QGroupBox):
    """Center-top panel: generates and plays a 30-second preview clip."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Preview", parent)
        self._song_paths: dict | None = None
        self._theme: Theme = load_theme()
        self._generation_stamp: int = 0
        self._rendered_stamp: int = -1
        self._temp_path: Path | None = None
        self._thread: QThread | None = None
        self._build_ui()

    # ──────────────────────────────────────────────────────────────────
    # Public slots
    # ──────────────────────────────────────────────────────────────────

    def song_loaded(self, paths: dict) -> None:
        """Called when a new song is selected in the song selector."""
        self._song_paths = paths
        self._generation_stamp += 1
        self._generate_btn.setEnabled(True)

        # Update start-time maximum from audio duration (best effort)
        audio_path = paths.get("audio")
        if audio_path:
            # Set a generous upper bound; exact duration unknown without loading
            self._start_spin.setMaximum(9999.0)

        self._update_stale_label()

    def on_theme_changed(self, theme: Theme) -> None:
        """Called when the theme editor emits theme_changed."""
        self._theme = theme
        self._generation_stamp += 1
        self._update_stale_label()

    # ──────────────────────────────────────────────────────────────────
    # UI construction
    # ──────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(6, 6, 6, 6)
        outer.setSpacing(4)

        # --- Video widget (hidden until first render) ---
        self._video_widget = QVideoWidget()
        self._video_widget.setMinimumHeight(120)
        outer.addWidget(self._video_widget, stretch=1)
        self._video_widget.hide()

        # --- Placeholder label ---
        self._placeholder_label = QLabel("Load a song to generate a preview.")
        self._placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._placeholder_label.setStyleSheet("color: gray; font-style: italic;")
        outer.addWidget(self._placeholder_label, stretch=1)

        # --- Controls bar ---
        controls = QHBoxLayout()
        controls.setSpacing(6)

        controls.addWidget(QLabel("Start:"))

        self._start_spin = QDoubleSpinBox()
        self._start_spin.setRange(0.0, 9999.0)
        self._start_spin.setSingleStep(5.0)
        self._start_spin.setSuffix("s")
        self._start_spin.setDecimals(1)
        self._start_spin.setFixedWidth(76)
        controls.addWidget(self._start_spin)

        self._generate_btn = QPushButton("Generate Preview")
        self._generate_btn.setEnabled(False)
        self._generate_btn.clicked.connect(self._on_generate_clicked)
        controls.addWidget(self._generate_btn)

        self._stale_label = QLabel("⚠ Regenerate")
        self._stale_label.setStyleSheet("color: orange;")
        self._stale_label.hide()
        controls.addWidget(self._stale_label)

        controls.addStretch()

        self._play_btn = QPushButton("▶")
        self._play_btn.setFixedWidth(32)
        self._play_btn.setEnabled(False)
        self._play_btn.clicked.connect(self._on_play_clicked)
        controls.addWidget(self._play_btn)

        self._time_label = QLabel("0:00 / 0:00")
        controls.addWidget(self._time_label)

        outer.addLayout(controls)

        # --- Progress bar (hidden when idle) ---
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 0)  # indeterminate
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setFixedHeight(6)
        self._progress_bar.hide()
        outer.addWidget(self._progress_bar)

        # --- Media player ---
        self._media_player = QMediaPlayer()
        self._audio_output = QAudioOutput()
        self._media_player.setVideoOutput(self._video_widget)
        self._media_player.setAudioOutput(self._audio_output)
        self._media_player.playbackStateChanged.connect(self._update_play_btn)
        self._media_player.positionChanged.connect(self._on_position_changed)
        self._media_player.durationChanged.connect(self._on_duration_changed)

    # ──────────────────────────────────────────────────────────────────
    # Generate
    # ──────────────────────────────────────────────────────────────────

    def _on_generate_clicked(self) -> None:
        if not self._song_paths or not self._song_paths.get("lyrics") or not self._song_paths.get("audio"):
            QMessageBox.warning(self, "Missing Files", "Song has no lyrics or audio path.")
            return

        # Stop any playing preview
        self._media_player.stop()

        # Clean up previous temp file
        if self._temp_path and self._temp_path.exists():
            try:
                os.unlink(self._temp_path)
            except OSError:
                pass

        # Create new temp file path
        fd, tmp = tempfile.mkstemp(suffix=".mp4", prefix="lyric_preview_")
        os.close(fd)
        self._temp_path = Path(tmp)

        # Disable controls while rendering
        self._generate_btn.setEnabled(False)
        self._play_btn.setEnabled(False)
        self._progress_bar.show()

        # Spawn worker thread
        self._thread = QThread(self)
        self._worker = _PreviewWorker(
            lyrics_path=self._song_paths["lyrics"],
            audio_path=self._song_paths["audio"],
            background_path=self._song_paths.get("background"),
            theme=self._theme,
            start_time=self._start_spin.value(),
            out_path=str(self._temp_path),
        )
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_render_finished)
        self._worker.error.connect(self._on_render_error)
        self._worker.finished.connect(self._thread.quit)
        self._worker.error.connect(self._thread.quit)
        self._thread.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.finished.connect(self._on_thread_done)
        self._thread.start()

    def _on_thread_done(self) -> None:
        self._thread = None

    # ──────────────────────────────────────────────────────────────────
    # Render callbacks
    # ──────────────────────────────────────────────────────────────────

    def _on_render_finished(self, path: str) -> None:
        self._progress_bar.hide()
        self._rendered_stamp = self._generation_stamp
        self._update_stale_label()

        # Load into media player
        from PyQt6.QtCore import QUrl
        self._media_player.setSource(QUrl.fromLocalFile(path))

        # Switch to video widget
        self._placeholder_label.hide()
        self._video_widget.show()

        self._generate_btn.setEnabled(True)
        self._play_btn.setEnabled(True)
        self._media_player.play()
        self._update_play_btn(self._media_player.playbackState())

    def _on_render_error(self, msg: str) -> None:
        self._progress_bar.hide()
        self._generate_btn.setEnabled(True)
        QMessageBox.critical(self, "Preview Error", f"Render failed:\n{msg}")

    # ──────────────────────────────────────────────────────────────────
    # Playback controls
    # ──────────────────────────────────────────────────────────────────

    def _on_play_clicked(self) -> None:
        if self._media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self._media_player.pause()
        else:
            self._media_player.play()

    def _update_play_btn(self, state: QMediaPlayer.PlaybackState) -> None:
        playing = state == QMediaPlayer.PlaybackState.PlayingState
        self._play_btn.setText("⏸" if playing else "▶")

    def _on_position_changed(self, ms: int) -> None:
        self._time_label.setText(
            f"{_fmt_ms(ms)} / {_fmt_ms(self._media_player.duration())}"
        )

    def _on_duration_changed(self, ms: int) -> None:
        self._time_label.setText(
            f"{_fmt_ms(self._media_player.position())} / {_fmt_ms(ms)}"
        )

    # ──────────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────────

    def _update_stale_label(self) -> None:
        stale = self._generation_stamp != self._rendered_stamp
        self._stale_label.setVisible(stale and self._rendered_stamp >= 0)


def _fmt_ms(ms: int) -> str:
    """Format milliseconds as M:SS."""
    s = ms // 1000
    return f"{s // 60}:{s % 60:02d}"
