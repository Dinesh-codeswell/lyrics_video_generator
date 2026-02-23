"""Main application window for the lyric video generator GUI."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
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

from src.gui.panels.song_selector import SongSelectorPanel


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Durt Nurs Lyric Video Generator")
        self.setMinimumSize(1280, 800)
        self.resize(1440, 900)

        self._build_menu_bar()

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        layout.addWidget(self._build_central_widget(), stretch=1)
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
        outer.addWidget(self._make_placeholder("Theme Editor", "Issue #30"))

        outer.setSizes([250, 760, 270])
        outer.setChildrenCollapsible(False)
        return outer

    def _build_center_splitter(self) -> QSplitter:
        center = QSplitter(Qt.Orientation.Vertical)
        center.addWidget(self._make_placeholder("Preview", "Issue #31"))
        center.addWidget(self._make_placeholder("Timeline Editor", "Issue #29"))
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
        pass

    def _on_new(self):
        pass

    def _on_open_theme(self):
        pass

    def _on_save_theme(self):
        pass

    def _on_about(self):
        QMessageBox.about(
            self,
            "About",
            "<b>Durt Nurs Lyric Video Generator</b><br>"
            "Generate YouTube-ready 1080p lyric videos<br>"
            "from a JSON lyrics file and an audio track.",
        )
