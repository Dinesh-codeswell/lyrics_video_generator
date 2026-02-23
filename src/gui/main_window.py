"""Main application window for the lyric video generator GUI."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from src.gui.audio_player import AudioPlayer
from src.gui.panels.song_selector import SongSelectorPanel
from src.gui.panels.theme_editor import ThemeEditorPanel
from src.gui.panels.timeline_editor import TimelineEditorPanel
from src.gui.panels.transport_controls import TransportControls


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Durt Nurs Lyric Video Generator")
        self.setMinimumSize(1280, 800)
        self.resize(1440, 900)

        self._build_menu_bar()

        self._audio_player = AudioPlayer(self)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        layout.addWidget(self._build_central_widget(), stretch=1)
        layout.addWidget(TransportControls(self._audio_player))
        layout.addWidget(self._build_export_bar())

        self.setCentralWidget(container)

    # ------------------------------------------------------------------
    # Menu bar
    # ------------------------------------------------------------------

    def _build_menu_bar(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("File")
        file_menu.addAction("New").triggered.connect(self._on_new)
        file_menu.addAction("Open Theme…").triggered.connect(self._on_open_theme)
        file_menu.addAction("Save Theme").triggered.connect(self._on_save_theme)
        file_menu.addSeparator()
        file_menu.addAction("Quit").triggered.connect(self.close)

        help_menu = menubar.addMenu("Help")
        help_menu.addAction("About").triggered.connect(self._on_about)

    # ------------------------------------------------------------------
    # Central widget (three-column splitter)
    # ------------------------------------------------------------------

    def _build_central_widget(self) -> QSplitter:
        outer = QSplitter(Qt.Orientation.Horizontal)

        self._song_selector = SongSelectorPanel()
        self._song_selector.song_loaded.connect(self._on_song_loaded)
        outer.addWidget(self._song_selector)
        outer.addWidget(self._build_center_splitter())
        self._theme_editor = ThemeEditorPanel()
        outer.addWidget(self._theme_editor)

        outer.setSizes([250, 760, 270])
        outer.setChildrenCollapsible(False)
        return outer

    def _build_center_splitter(self) -> QSplitter:
        center = QSplitter(Qt.Orientation.Vertical)
        center.addWidget(self._make_placeholder("Preview", "Issue #31"))
        self._timeline = TimelineEditorPanel(self._audio_player)
        center.addWidget(self._timeline)
        center.setSizes([400, 260])
        center.setChildrenCollapsible(False)
        return center

    # ------------------------------------------------------------------
    # Export bar
    # ------------------------------------------------------------------

    def _build_export_bar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(52)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)

        progress = QProgressBar()
        progress.setValue(0)
        progress.setEnabled(False)
        progress.setTextVisible(True)
        progress.setFormat("Ready")

        export_btn = QPushButton("Export Video")
        export_btn.setEnabled(False)
        export_btn.setFixedWidth(120)

        layout.addWidget(QLabel("Export Controls (Issue #32):"))
        layout.addWidget(progress, stretch=1)
        layout.addWidget(export_btn)
        return bar

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _make_placeholder(title: str, issue: str) -> QGroupBox:
        box = QGroupBox(title)
        inner = QVBoxLayout(box)
        label = QLabel(f"Coming in {issue}")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("color: gray; font-style: italic;")
        inner.addWidget(label)
        return box

    # ------------------------------------------------------------------
    # Menu actions (stubs for future issues)
    # ------------------------------------------------------------------

    def _on_song_loaded(self, paths: dict):
        if paths.get("audio"):
            self._audio_player.load(paths["audio"])
        self._timeline.load_song(paths)

    def _on_new(self):
        pass

    def _on_open_theme(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Theme", "themes/", "JSON (*.json)"
        )
        if path:
            self._theme_editor.load_theme_file(path)

    def _on_save_theme(self):
        self._theme_editor.save_theme()

    def _on_about(self):
        QMessageBox.about(
            self,
            "About",
            "<b>Durt Nurs Lyric Video Generator</b><br>"
            "Generate YouTube-ready 1080p lyric videos<br>"
            "from a JSON lyrics file and an audio track.",
        )
