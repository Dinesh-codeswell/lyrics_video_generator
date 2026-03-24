"""Dialog for importing existing audio, lyrics, and background files into LV-Gen."""

import re
import shutil
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.core.song_resolver import (
    AUDIO_EXTENSIONS,
    INPUT_AUDIO_DIR,
    INPUT_BACKGROUNDS_DIR,
    INPUT_LYRICS_DIR,
)
from src.gui.dialogs.new_song_dialog import NewSongDialog


def _derive_slug(title: str) -> str:
    """Lowercase title, replace whitespace with hyphens, strip non-alphanumeric/hyphen chars."""
    slug = title.lower().strip()
    slug = re.sub(r"\s+", "-", slug)
    slug = re.sub(r"[^a-z0-9\-]", "", slug)
    slug = re.sub(r"-{2,}", "-", slug)
    return slug.strip("-")


class ImportSongDialog(QDialog):
    """Modal dialog that copies audio, lyrics, and optional background files into input/."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Import Song Files")
        self.setMinimumWidth(560)
        self.result_slug: str = ""
        self._slug_auto = True
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("e.g. My Song")
        self._name_edit.textChanged.connect(self._on_name_changed)
        form.addRow("Song name:", self._name_edit)

        self._slug_edit = QLineEdit()
        self._slug_edit.setPlaceholderText("e.g. my-song")
        self._slug_edit.textEdited.connect(self._on_slug_edited)
        form.addRow("Filename slug:", self._slug_edit)

        slug_hint = QLabel("Used as the filename for all copied files.")
        slug_hint.setStyleSheet("color: #888; font-size: 11px;")
        form.addRow("", slug_hint)

        layout.addLayout(form)

        # Audio file
        layout.addWidget(QLabel("Audio File (required):"))
        audio_row = QHBoxLayout()
        self._audio_path = QLineEdit()
        self._audio_path.setReadOnly(True)
        self._audio_path.setPlaceholderText("No file selected")
        audio_row.addWidget(self._audio_path, stretch=1)
        audio_browse = QPushButton("Browse…")
        audio_browse.clicked.connect(self._browse_audio)
        audio_row.addWidget(audio_browse)
        layout.addLayout(audio_row)
        audio_hint = QLabel("Supported: " + ", ".join(AUDIO_EXTENSIONS))
        audio_hint.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(audio_hint)

        # Lyrics JSON
        layout.addWidget(QLabel("Lyrics JSON (required):"))
        lyrics_row = QHBoxLayout()
        self._lyrics_path = QLineEdit()
        self._lyrics_path.setReadOnly(True)
        self._lyrics_path.setPlaceholderText("No file selected")
        lyrics_row.addWidget(self._lyrics_path, stretch=1)
        lyrics_browse = QPushButton("Browse…")
        lyrics_browse.clicked.connect(self._browse_lyrics)
        lyrics_row.addWidget(lyrics_browse)
        lyrics_create = QPushButton("Create from Text…")
        lyrics_create.clicked.connect(self._create_lyrics_from_text)
        lyrics_row.addWidget(lyrics_create)
        layout.addLayout(lyrics_row)

        # Background video
        layout.addWidget(QLabel("Background Video (optional):"))
        bg_row = QHBoxLayout()
        self._bg_path = QLineEdit()
        self._bg_path.setReadOnly(True)
        self._bg_path.setPlaceholderText("No file selected — will use solid color background")
        bg_row.addWidget(self._bg_path, stretch=1)
        bg_browse = QPushButton("Browse…")
        bg_browse.clicked.connect(self._browse_background)
        bg_row.addWidget(bg_browse)
        bg_clear = QPushButton("Clear")
        bg_clear.clicked.connect(lambda: self._bg_path.clear())
        bg_row.addWidget(bg_clear)
        layout.addLayout(bg_row)

        note = QLabel("Files will be copied into the input/ directories.")
        note.setStyleSheet("color: #888; font-size: 11px; font-style: italic; margin-top: 6px;")
        layout.addWidget(note)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Import")
        buttons.accepted.connect(self._on_import)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # ------------------------------------------------------------------
    # Slug auto-derivation
    # ------------------------------------------------------------------

    def _on_name_changed(self, text: str) -> None:
        if self._slug_auto:
            self._slug_edit.blockSignals(True)
            self._slug_edit.setText(_derive_slug(text))
            self._slug_edit.blockSignals(False)

    def _on_slug_edited(self, _text: str) -> None:
        self._slug_auto = False

    # ------------------------------------------------------------------
    # File pickers
    # ------------------------------------------------------------------

    def _browse_audio(self) -> None:
        exts = " ".join(f"*{e}" for e in AUDIO_EXTENSIONS)
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Audio File", "", f"Audio Files ({exts})"
        )
        if path:
            self._audio_path.setText(path)

    def _browse_lyrics(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Lyrics JSON", "", "Lyrics JSON (*.json)"
        )
        if path:
            self._lyrics_path.setText(path)

    def _create_lyrics_from_text(self) -> None:
        dlg = NewSongDialog(self)
        if dlg.exec() == NewSongDialog.DialogCode.Accepted and dlg.result_slug:
            created_path = INPUT_LYRICS_DIR / f"{dlg.result_slug}.json"
            self._lyrics_path.setText(str(created_path))
            if not self._slug_edit.text().strip():
                self._slug_auto = False
                self._slug_edit.setText(dlg.result_slug)

    def _browse_background(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Background Video", "", "Video Files (*.mp4)"
        )
        if path:
            self._bg_path.setText(path)

    # ------------------------------------------------------------------
    # Import / validate
    # ------------------------------------------------------------------

    def _on_import(self) -> None:
        slug = self._slug_edit.text().strip()
        audio = self._audio_path.text().strip()
        lyrics = self._lyrics_path.text().strip()
        background = self._bg_path.text().strip()

        errors = []
        if not slug:
            errors.append("Song name / filename slug is required.")
        if not audio:
            errors.append("Audio file is required.")
        elif not Path(audio).exists():
            errors.append(f"Audio file not found:\n  {audio}")
        if not lyrics:
            errors.append("Lyrics JSON is required.")
        elif not Path(lyrics).exists():
            errors.append(f"Lyrics file not found:\n  {lyrics}")
        if background and not Path(background).exists():
            errors.append(f"Background file not found:\n  {background}")

        if errors:
            QMessageBox.warning(self, "Missing or Invalid Files", "\n".join(errors))
            return

        audio_ext = Path(audio).suffix
        dest_audio = INPUT_AUDIO_DIR / f"{slug}{audio_ext}"
        dest_lyrics = INPUT_LYRICS_DIR / f"{slug}.json"
        dest_bg = (INPUT_BACKGROUNDS_DIR / f"{slug}.mp4") if background else None

        existing = [str(p) for p in [dest_audio, dest_lyrics, dest_bg] if p and p.exists()]
        if existing:
            ans = QMessageBox.question(
                self,
                "Files Already Exist",
                "The following files already exist and will be overwritten:\n"
                + "\n".join(f"  • {p}" for p in existing)
                + "\n\nContinue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if ans != QMessageBox.StandardButton.Yes:
                return

        try:
            INPUT_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
            INPUT_LYRICS_DIR.mkdir(parents=True, exist_ok=True)
            if dest_bg:
                INPUT_BACKGROUNDS_DIR.mkdir(parents=True, exist_ok=True)
            shutil.copy2(audio, dest_audio)
            shutil.copy2(lyrics, dest_lyrics)
            if dest_bg:
                shutil.copy2(background, dest_bg)
        except OSError as exc:
            QMessageBox.critical(self, "Copy Error", str(exc))
            return

        self.result_slug = slug
        self.accept()
