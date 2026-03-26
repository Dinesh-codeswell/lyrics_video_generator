"""Main application window for the lyric video generator GUI."""

import sys
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QAbstractSpinBox,
    QApplication,
    QDialog,
    QFileDialog,
    QGroupBox,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.core.song_resolver import THEMES_DIR
from src.gui.audio_player import AudioPlayer
from src.gui.panels.export_bar import ExportBar
from src.gui.panels.preview_panel import PreviewPanel
from src.gui.panels.song_selector import SongSelectorPanel
from src.gui.panels.theme_editor import ThemeEditorPanel
from src.gui.panels.timeline_editor import TimelineEditorPanel
from src.gui.panels.transport_controls import TransportControls


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._song_name: str = ""
        self._lyrics_dirty: bool = False
        self._theme_dirty: bool = False

        _icon_path = Path(__file__).parents[2] / "assets" / "icon.png"
        if _icon_path.exists():
            self.setWindowIcon(QIcon(str(_icon_path)))
            if sys.platform == "darwin":
                self.setWindowFilePath(str(_icon_path))

        self._update_title()
        screen = QApplication.primaryScreen().availableGeometry()
        win_w = max(1400, min(1800, int(screen.width() * 0.90)))
        win_h = max(900, min(1000, int(screen.height() * 0.90)))
        self.setMinimumSize(1400, 900)
        self.resize(win_w, win_h)
        self._initial_win_w = win_w

        self._build_menu_bar()

        self._audio_player = AudioPlayer(self)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        layout.addWidget(self._build_central_widget(), stretch=1)
        layout.addWidget(TransportControls(self._audio_player))
        self._export_bar = ExportBar()
        layout.addWidget(self._export_bar)

        # Cross-panel wiring (all panels now exist)
        self._theme_editor.theme_changed.connect(self._export_bar.on_theme_changed)
        self._timeline.lyrics_modified.connect(self._on_lyrics_dirty)
        self._timeline.lyrics_saved.connect(self._on_lyrics_saved)
        self._theme_editor.theme_dirty_changed.connect(self._on_theme_dirty)
        self._export_bar.set_pre_export_check(self._check_dirty_before_export)

        # Preview → timeline cursor sync
        self._preview.preview_playback_started.connect(self._timeline.on_preview_started)
        self._preview.preview_position_changed.connect(self._timeline.on_preview_position)
        self._preview.preview_playback_stopped.connect(self._timeline.on_preview_stopped)

        self.setCentralWidget(container)
        self._build_shortcuts()

    # ------------------------------------------------------------------
    # Menu bar
    # ------------------------------------------------------------------

    def _build_menu_bar(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("File")
        file_menu.addAction("New Song from Text\u2026").triggered.connect(self._on_new)
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

        # Connect theme changes to preview staleness tracking (both panels now exist)
        self._theme_editor.theme_changed.connect(self._preview.on_theme_changed)

        left_w = 250
        right_w = 350
        center_w = self._initial_win_w - left_w - right_w
        outer.setSizes([left_w, center_w, right_w])
        outer.setChildrenCollapsible(False)
        return outer

    def _build_center_splitter(self) -> QSplitter:
        center = QSplitter(Qt.Orientation.Vertical)
        self._preview = PreviewPanel()
        center.addWidget(self._preview)
        self._timeline = TimelineEditorPanel(self._audio_player)
        center.addWidget(self._timeline)
        center.setSizes([400, 260])
        center.setChildrenCollapsible(False)
        return center

    # ------------------------------------------------------------------
    # Shortcuts
    # ------------------------------------------------------------------

    def _build_shortcuts(self) -> None:
        QShortcut(QKeySequence.StandardKey.Save, self).activated.connect(
            self._timeline.save_lyrics
        )
        QShortcut(QKeySequence("Ctrl+Shift+S"), self).activated.connect(
            self._theme_editor.save_theme
        )
        QShortcut(QKeySequence.StandardKey.Undo, self).activated.connect(
            self._timeline.undo
        )
        QShortcut(QKeySequence.StandardKey.Redo, self).activated.connect(
            self._timeline.redo
        )
        QShortcut(QKeySequence(Qt.Key.Key_Space), self).activated.connect(
            self._on_space
        )
        QShortcut(QKeySequence(Qt.Key.Key_Return), self).activated.connect(
            self._on_stamp
        )
        QShortcut(QKeySequence(Qt.Key.Key_Enter), self).activated.connect(
            self._on_stamp
        )
        QShortcut(QKeySequence(Qt.Key.Key_Left), self).activated.connect(
            lambda: self._on_step(-1)
        )
        QShortcut(QKeySequence(Qt.Key.Key_Right), self).activated.connect(
            lambda: self._on_step(1)
        )

    def _on_step(self, direction: int) -> None:
        fw = QApplication.focusWidget()
        if isinstance(fw, (QLineEdit, QTextEdit, QAbstractSpinBox)):
            return
        if self._audio_player.is_playing:
            return
        step_ms = self._timeline.step_size_ms
        snapped = round(self._audio_player.position / step_ms) * step_ms
        new_pos = max(0, snapped + direction * step_ms)
        self._audio_player.seek(new_pos)

    def _on_space(self) -> None:
        fw = QApplication.focusWidget()
        if isinstance(fw, (QLineEdit, QTextEdit, QAbstractSpinBox)):
            return
        if self._audio_player.is_playing:
            self._audio_player.pause()
        else:
            self._audio_player.play()

    def _on_stamp(self) -> None:
        fw = QApplication.focusWidget()
        if isinstance(fw, (QLineEdit, QTextEdit, QAbstractSpinBox)):
            return
        self._timeline.stamp_current()

    # ------------------------------------------------------------------
    # Dirty / title tracking
    # ------------------------------------------------------------------

    def _on_lyrics_dirty(self) -> None:
        self._lyrics_dirty = True
        self._update_title()

    def _on_lyrics_saved(self) -> None:
        self._lyrics_dirty = False
        self._update_title()

    def _on_theme_dirty(self, dirty: bool) -> None:
        self._theme_dirty = dirty
        self._update_title()

    def _update_title(self) -> None:
        base = "Lyric Video Generator"
        dirty = self._lyrics_dirty or self._theme_dirty
        prefix = "• " if dirty else ""
        name_part = f"{self._song_name} — " if self._song_name else ""
        self.setWindowTitle(f"{prefix}{name_part}{base}")

    def _check_dirty_before_export(self) -> bool:
        msgs = []
        if self._lyrics_dirty:
            msgs.append("lyrics")
        if self._theme_dirty:
            msgs.append("theme")
        if not msgs:
            return True
        ans = QMessageBox.question(
            self,
            "Unsaved Changes",
            f"Unsaved changes to {', '.join(msgs)}. Export anyway?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        return ans == QMessageBox.StandardButton.Yes

    # ------------------------------------------------------------------
    # Close event
    # ------------------------------------------------------------------

    def closeEvent(self, event) -> None:  # noqa: N802
        msgs = []
        if self._lyrics_dirty:
            msgs.append("lyrics")
        if self._theme_dirty:
            msgs.append("theme")
        if msgs:
            ans = QMessageBox.question(
                self,
                "Unsaved Changes",
                f"You have unsaved changes to: {', '.join(msgs)}.\nClose anyway?",
                QMessageBox.StandardButton.Save
                | QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel,
            )
            if ans == QMessageBox.StandardButton.Save:
                if self._lyrics_dirty:
                    self._timeline.save_lyrics()
                if self._theme_dirty:
                    self._theme_editor.save_theme()
            elif ans == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return
        event.accept()

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
    # Menu actions
    # ------------------------------------------------------------------

    def _on_song_loaded(self, paths: dict):
        msgs = []
        if self._lyrics_dirty:
            msgs.append("lyrics")
        if self._theme_dirty:
            msgs.append("theme")
        if msgs:
            ans = QMessageBox.question(
                self,
                "Unsaved Changes",
                f"You have unsaved changes to {', '.join(msgs)}. Discard and load new song?",
                QMessageBox.StandardButton.Save
                | QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel,
            )
            if ans == QMessageBox.StandardButton.Save:
                if self._lyrics_dirty:
                    self._timeline.save_lyrics()
                if self._theme_dirty:
                    self._theme_editor.save_theme()
            elif ans == QMessageBox.StandardButton.Cancel:
                return

        audio = paths.get("audio")
        self._song_name = Path(audio).stem if audio else ""
        self._lyrics_dirty = False
        self._update_title()

        if audio:
            self._audio_player.load(audio)
        self._timeline.load_song(paths)
        self._preview.song_loaded(paths)
        self._export_bar.song_loaded(paths)

        # Auto-load per-song theme
        theme_path = paths.get("theme")
        if theme_path:
            self._theme_editor.load_theme_file(theme_path)
        else:
            per_song_path = str(THEMES_DIR / f"{self._song_name}.json")
            self._theme_editor.reset_for_song(per_song_path)

    def _on_new(self):
        from src.core.song_resolver import resolve_song, scan_songs
        from src.gui.dialogs.new_song_dialog import NewSongDialog

        dlg = NewSongDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        slug = dlg.result_slug
        self._song_selector.scan()

        # Auto-load if audio is already present
        songs = {s.name: s for s in scan_songs()}
        info = songs.get(slug)
        if info and info.is_loadable:
            paths = resolve_song(slug)
            self._song_selector._loaded_name = slug
            self._song_selector._loaded_label.setText(f"Loaded: {slug}")
            self._on_song_loaded({k: str(v) if v else None for k, v in paths.items()})

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
            "<b>Lyric Video Generator</b><br>"
            "Generate YouTube-ready 1080p lyric videos<br>"
            "from a JSON lyrics file and an audio track.",
        )
