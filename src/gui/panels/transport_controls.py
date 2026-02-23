"""Transport controls widget — play/pause, stop, seek, time display."""

from PyQt6.QtCore import Qt
from PyQt6.QtMultimedia import QMediaPlayer
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QWidget,
)

from src.gui.audio_player import AudioPlayer


def _fmt_ms(ms: int) -> str:
    """Format milliseconds as M:SS."""
    total_s = max(0, ms) // 1000
    return f"{total_s // 60}:{total_s % 60:02d}"


class TransportControls(QWidget):
    """Shared transport bar connected to an AudioPlayer instance."""

    def __init__(self, player: AudioPlayer, parent: QWidget | None = None):
        super().__init__(parent)
        self._player = player
        self._duration_ms: int = 0
        self._seeking = False

        self._build_ui()
        self._connect_player()
        self._update_buttons(QMediaPlayer.PlaybackState.StoppedState)

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 2, 8, 2)
        layout.setSpacing(6)

        self._play_btn = QPushButton("▶")
        self._play_btn.setFixedWidth(36)
        self._play_btn.setToolTip("Play / Pause")
        self._play_btn.clicked.connect(self._on_play_pause)

        self._stop_btn = QPushButton("■")
        self._stop_btn.setFixedWidth(36)
        self._stop_btn.setToolTip("Stop")
        self._stop_btn.setEnabled(False)
        self._stop_btn.clicked.connect(self._player.stop)

        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(0, 0)
        self._slider.setEnabled(False)
        self._slider.sliderPressed.connect(self._on_slider_pressed)
        self._slider.sliderReleased.connect(self._on_slider_released)

        self._time_label = QLabel("0:00 / 0:00")
        self._time_label.setFixedWidth(90)
        self._time_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        layout.addWidget(self._play_btn)
        layout.addWidget(self._stop_btn)
        layout.addWidget(self._slider, stretch=1)
        layout.addWidget(self._time_label)

    # ------------------------------------------------------------------
    # Player → UI
    # ------------------------------------------------------------------

    def _connect_player(self):
        self._player.position_changed.connect(self._on_position_changed)
        self._player.duration_changed.connect(self._on_duration_changed)
        self._player.playback_state_changed.connect(self._update_buttons)

    def _on_position_changed(self, ms: int):
        if not self._seeking:
            self._slider.setValue(ms)
        self._time_label.setText(f"{_fmt_ms(ms)} / {_fmt_ms(self._duration_ms)}")

    def _on_duration_changed(self, ms: int):
        self._duration_ms = ms
        self._slider.setRange(0, ms)
        self._slider.setEnabled(ms > 0)
        self._time_label.setText(f"{_fmt_ms(self._player.position)} / {_fmt_ms(ms)}")

    def _update_buttons(self, state: QMediaPlayer.PlaybackState):
        playing = state == QMediaPlayer.PlaybackState.PlayingState
        stopped = state == QMediaPlayer.PlaybackState.StoppedState
        self._play_btn.setText("⏸" if playing else "▶")
        self._stop_btn.setEnabled(not stopped)
        self._play_btn.setEnabled(self._duration_ms > 0)

    # ------------------------------------------------------------------
    # UI → Player
    # ------------------------------------------------------------------

    def _on_play_pause(self):
        if self._player.is_playing:
            self._player.pause()
        else:
            self._player.play()

    def _on_slider_pressed(self):
        self._seeking = True

    def _on_slider_released(self):
        self._player.seek(self._slider.value())
        self._seeking = False
