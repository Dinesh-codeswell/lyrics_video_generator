"""Dialog for creating a new lyrics JSON scaffold from plain text."""

import json
import re
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.core.song_resolver import INPUT_LYRICS_DIR
from src.gui.styles import TOKENS


def _derive_slug(title: str) -> str:
    """Lowercase title, replace whitespace with hyphens, strip non-alphanumeric/hyphen chars."""
    slug = title.lower().strip()
    slug = re.sub(r"\s+", "-", slug)
    slug = re.sub(r"[^a-z0-9\-]", "", slug)
    slug = re.sub(r"-{2,}", "-", slug)
    return slug.strip("-")


def _build_entries(text: str) -> list[dict]:
    """Convert raw lyrics text into JSON entry list with gap markers for blank lines.

    - Blank lines → {"time": 0.0, "text": ""} (music gap marker)
    - Multiple consecutive blank lines → collapsed to one gap entry
    - Leading/trailing gap entries stripped before the required end marker is appended
    """
    entries: list[dict] = []
    prev_blank = False
    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if stripped == "":
            if not prev_blank:
                entries.append({"time": 0.0, "text": ""})
            prev_blank = True
        else:
            entries.append({"time": 0.0, "text": stripped})
            prev_blank = False

    # Strip leading gap entries
    while entries and entries[0]["text"] == "":
        entries.pop(0)
    # Strip trailing gap entries
    while entries and entries[-1]["text"] == "":
        entries.pop()

    # Append required end marker
    entries.append({"time": 0.0, "text": ""})
    return entries


class NewSongDialog(QDialog):
    """Modal dialog that scaffolds a zero-based lyrics JSON file from plain text."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("New Song from Text")
        self.setMinimumWidth(520)
        self.result_slug: str = ""
        self._slug_auto = True  # track whether slug has been manually edited

        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._title_edit = QLineEdit()
        self._title_edit.setPlaceholderText("e.g. My New Song")
        self._title_edit.textChanged.connect(self._on_title_changed)
        form.addRow("Title:", self._title_edit)

        self._artist_edit = QLineEdit()
        self._artist_edit.setPlaceholderText("e.g. Band Name")
        form.addRow("Artist:", self._artist_edit)

        self._slug_edit = QLineEdit()
        self._slug_edit.setPlaceholderText("e.g. my-new-song")
        self._slug_edit.textEdited.connect(self._on_slug_edited)
        form.addRow("Filename slug:", self._slug_edit)

        slug_hint = QLabel("Saved to input/lyrics/<slug>.json")
        slug_hint.setProperty("secondary", "true")
        form.addRow("", slug_hint)

        layout.addLayout(form)

        lyrics_label = QLabel("Lyrics (one line per lyric line):")
        layout.addWidget(lyrics_label)

        self._lyrics_edit = QTextEdit()
        self._lyrics_edit.setPlaceholderText(
            "Paste or type lyrics here.\n\nOne lyric line per line."
        )
        self._lyrics_edit.setMinimumHeight(240)
        self._lyrics_edit.setStyleSheet(f"background-color: {TOKENS['slate_card']}; border: 1px solid {TOKENS['steel_border']}; border-radius: {TOKENS['radius_md']};")
        layout.addWidget(self._lyrics_edit, stretch=1)

        gap_hint = QLabel("Blank lines are preserved as music gap markers.")
        gap_hint.setProperty("secondary", "true")
        layout.addWidget(gap_hint)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Create")
        buttons.accepted.connect(self._on_create)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # ------------------------------------------------------------------
    # Slug auto-derivation
    # ------------------------------------------------------------------

    def _on_title_changed(self, text: str) -> None:
        if self._slug_auto:
            self._slug_edit.blockSignals(True)
            self._slug_edit.setText(_derive_slug(text))
            self._slug_edit.blockSignals(False)

    def _on_slug_edited(self, text: str) -> None:
        # Once the user manually edits the slug, stop auto-updating it
        self._slug_auto = False

    # ------------------------------------------------------------------
    # Create / validate
    # ------------------------------------------------------------------

    def _on_create(self) -> None:
        title = self._title_edit.text().strip()
        artist = self._artist_edit.text().strip()
        slug = self._slug_edit.text().strip()
        raw_text = self._lyrics_edit.toPlainText()

        # Validate inputs
        errors = []
        if not title:
            errors.append("Title is required.")
        if not artist:
            errors.append("Artist is required.")
        if not slug:
            errors.append("Filename slug is required.")

        entries = _build_entries(raw_text)
        # entries always ends with end marker; check there's at least one lyric line
        lyric_lines = [e for e in entries if e["text"] != ""]
        if not lyric_lines:
            errors.append("At least one lyric line is required.")

        if errors:
            QMessageBox.warning(self, "Missing Information", "\n".join(errors))
            return

        out_path = INPUT_LYRICS_DIR / f"{slug}.json"

        # Overwrite guard
        if out_path.exists():
            ans = QMessageBox.question(
                self,
                "File Already Exists",
                f"'{out_path.name}' already exists.\nOverwrite it?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if ans != QMessageBox.StandardButton.Yes:
                return

        # Write JSON
        payload = {"title": title, "artist": artist, "lyrics": entries}
        try:
            out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
        except OSError as exc:
            QMessageBox.critical(self, "Write Error", str(exc))
            return

        self.result_slug = slug
        self.accept()
