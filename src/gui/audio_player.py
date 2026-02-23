"""Shared audio playback service wrapping QMediaPlayer."""

from PyQt6.QtCore import QObject, QUrl, pyqtSignal
from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer


class AudioPlayer(QObject):
    """Shared audio playback service.

    Signals:
        position_changed(int)  — current position in milliseconds
        duration_changed(int)  — total duration in milliseconds (once known)
        playback_state_changed(QMediaPlayer.PlaybackState)
    """

    position_changed = pyqtSignal(int)
    duration_changed = pyqtSignal(int)
    playback_state_changed = pyqtSignal(QMediaPlayer.PlaybackState)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)

        self._player = QMediaPlayer(self)
        self._audio_output = QAudioOutput(self)
        self._player.setAudioOutput(self._audio_output)
        self._audio_output.setVolume(1.0)

        self._player.positionChanged.connect(self.position_changed)
        self._player.durationChanged.connect(self.duration_changed)
        self._player.playbackStateChanged.connect(self.playback_state_changed)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load(self, path: str) -> None:
        """Load an audio file. Stops any current playback."""
        self._player.stop()
        self._player.setSource(QUrl.fromLocalFile(path))

    def play(self) -> None:
        self._player.play()

    def pause(self) -> None:
        self._player.pause()

    def stop(self) -> None:
        self._player.stop()

    def seek(self, position_ms: int) -> None:
        """Seek to position in milliseconds."""
        self._player.setPosition(position_ms)

    @property
    def duration(self) -> int:
        """Total duration in milliseconds (0 if not yet known)."""
        return self._player.duration()

    @property
    def position(self) -> int:
        """Current position in milliseconds."""
        return self._player.position()

    @property
    def is_playing(self) -> bool:
        return self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
