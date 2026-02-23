"""Song selector panel — left sidebar of the main window."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.core.song_resolver import SongInfo, resolve_song, scan_songs


class _SongListItem(QListWidgetItem):
    """List item representing a single discovered song."""

    def __init__(self, info: SongInfo):
        super().__init__()
        self.info = info
        self._refresh_text()

    def _refresh_text(self):
        presence = (
            f"  {'✓' if self.info.has_lyrics else '✗'} lyrics  "
            f"{'✓' if self.info.has_audio else '✗'} audio  "
            f"{'✓' if self.info.has_background else '✗'} bg"
        )
        self.setText(f"♪  {self.info.name}\n{presence}")

        if not self.info.is_loadable:
            self.setForeground(QColor("gray"))


class SongSelectorPanel(QGroupBox):
    """Left sidebar panel for browsing and loading songs from input/ folders."""

    song_loaded = pyqtSignal(dict)

    def __init__(self, parent: QWidget | None = None):
        super().__init__("Song Selector", parent)
        self._loaded_name: str | None = None
        self._build_ui()
        self._scan()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(6)

        self._loaded_label = QLabel("Loaded: —")
        self._loaded_label.setStyleSheet("font-style: italic; color: #555;")
        self._loaded_label.setWordWrap(True)
        layout.addWidget(self._loaded_label)

        self._list = QListWidget()
        self._list.setAlternatingRowColors(True)
        self._list.itemDoubleClicked.connect(self._load_selected)
        layout.addWidget(self._list, stretch=1)

        btn_row = QHBoxLayout()
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._scan)

        self._load_btn = QPushButton("Load Song")
        self._load_btn.setEnabled(False)
        self._load_btn.clicked.connect(self._load_selected)

        btn_row.addWidget(refresh_btn)
        btn_row.addStretch()
        btn_row.addWidget(self._load_btn)
        layout.addLayout(btn_row)

        self._list.currentItemChanged.connect(self._on_selection_changed)

    # ------------------------------------------------------------------
    # Scanning
    # ------------------------------------------------------------------

    def _scan(self):
        self._list.clear()
        songs = scan_songs()

        if not songs:
            placeholder = QListWidgetItem("No songs found in input/")
            placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
            placeholder.setForeground(QColor("gray"))
            self._list.addItem(placeholder)
            self._load_btn.setEnabled(False)
            return

        for info in songs:
            self._list.addItem(_SongListItem(info))

        self._load_btn.setEnabled(False)

    # ------------------------------------------------------------------
    # Interaction
    # ------------------------------------------------------------------

    def _on_selection_changed(self, current: QListWidgetItem | None, _prev):
        if isinstance(current, _SongListItem):
            self._load_btn.setEnabled(current.info.is_loadable)
        else:
            self._load_btn.setEnabled(False)

    def _load_selected(self, item: QListWidgetItem | None = None):
        if item is None:
            item = self._list.currentItem()

        if not isinstance(item, _SongListItem):
            return

        if not item.info.is_loadable:
            QMessageBox.warning(
                self,
                "Cannot Load Song",
                f"'{item.info.name}' is missing required files.\n"
                "Both a lyrics JSON and an audio file are required.",
            )
            return

        try:
            paths = resolve_song(item.info.name)
        except Exception as exc:
            QMessageBox.critical(self, "Load Error", str(exc))
            return

        self._loaded_name = item.info.name
        self._loaded_label.setText(f"Loaded: {item.info.name}")
        self.song_loaded.emit({k: str(v) if v else None for k, v in paths.items()})
