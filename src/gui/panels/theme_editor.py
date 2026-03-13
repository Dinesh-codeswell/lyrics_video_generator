"""Theme editor panel — right sidebar for editing all theme properties."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFontDatabase
from PyQt6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from src.core.theme_loader import DEFAULTS, Theme, load_theme


# ──────────────────────────────────────────────────────────────────────────────
# _ColorButton
# ──────────────────────────────────────────────────────────────────────────────

class _ColorButton(QPushButton):
    """Small button that shows a color swatch and opens QColorDialog on click."""

    color_changed = pyqtSignal(str)  # emits hex string e.g. "#ff0000"

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._hex: str = "#000000"
        self.setFixedSize(36, 24)
        self.clicked.connect(self._open_dialog)

    # ------------------------------------------------------------------

    def set_color(self, hex_color: str) -> None:
        """Set button color without emitting color_changed."""
        self._hex = hex_color
        self.setStyleSheet(
            f"background-color: {hex_color}; border: 1px solid #555; border-radius: 3px;"
        )

    def color(self) -> str:
        return self._hex

    # ------------------------------------------------------------------

    def _open_dialog(self) -> None:
        initial = QColor(self._hex)
        chosen = QColorDialog.getColor(initial, self, "Pick colour")
        if chosen.isValid():
            hex_str = chosen.name().upper()
            self.set_color(hex_str)
            self.color_changed.emit(hex_str)


# ──────────────────────────────────────────────────────────────────────────────
# _CollapsibleSection
# ──────────────────────────────────────────────────────────────────────────────

class _CollapsibleSection(QWidget):
    """A titled section that can be collapsed/expanded with a toggle button."""

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._toggle_btn = QPushButton(f"▼  {title}")
        self._toggle_btn.setCheckable(True)
        self._toggle_btn.setChecked(True)
        self._toggle_btn.setFlat(True)
        self._toggle_btn.setStyleSheet(
            "text-align: left; padding: 4px 6px; font-weight: bold;"
        )
        self._toggle_btn.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self._toggle_btn.toggled.connect(self._on_toggled)
        outer.addWidget(self._toggle_btn)

        self._content = QWidget()
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(8, 2, 4, 6)
        self._content_layout.setSpacing(4)
        outer.addWidget(self._content)

        self._title = title

    # ------------------------------------------------------------------

    def add_row(self, label: str, *widgets: QWidget) -> None:
        """Add a labelled row of widgets to this section's content area."""
        row = QHBoxLayout()
        row.setSpacing(6)
        lbl = QLabel(label)
        lbl.setFixedWidth(72)
        lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        row.addWidget(lbl)
        for w in widgets:
            row.addWidget(w)
        row.addStretch()
        self._content_layout.addLayout(row)

    # ------------------------------------------------------------------

    def _on_toggled(self, checked: bool) -> None:
        self._content.setVisible(checked)
        self._toggle_btn.setText(f"{'▼' if checked else '▶'}  {self._title}")


# ──────────────────────────────────────────────────────────────────────────────
# ThemeEditorPanel
# ──────────────────────────────────────────────────────────────────────────────

class ThemeEditorPanel(QGroupBox):
    """Right-sidebar panel for live editing of all theme properties."""

    theme_changed      = pyqtSignal(object)  # emits Theme on any change
    theme_dirty_changed = pyqtSignal(bool)   # True = has unsaved changes

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Theme Editor", parent)
        self._theme: Theme = load_theme()
        self._filepath: Path | None = None
        self._blocking: bool = False
        self._dirty: bool = False
        self._build_ui()
        self._populate_controls()

    # ──────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────

    def load_theme_file(self, path: str | None) -> None:
        """Load a theme JSON file and populate all controls."""
        try:
            self._theme = load_theme(path)
            self._filepath = Path(path) if path else None
        except (FileNotFoundError, ValueError) as exc:
            QMessageBox.critical(self, "Load Error", str(exc))
            return
        self._populate_controls()
        self.theme_changed.emit(self._theme)

    def save_theme(self, path: str | None = None) -> None:
        """Write the current in-memory theme to disk.

        If *path* is None, uses self._filepath.  If neither is set, prompts for
        a file path.
        """
        target = path or (str(self._filepath) if self._filepath else None)
        if not target:
            target, _ = QFileDialog.getSaveFileName(
                self, "Save Theme As", "themes/", "JSON (*.json)"
            )
            if not target:
                return

        self._filepath = Path(target)
        data = asdict(self._theme)
        try:
            with open(self._filepath, "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2)
            self._set_theme_dirty(False)
        except OSError as exc:
            QMessageBox.critical(self, "Save Error", str(exc))

    def get_theme(self) -> Theme:
        return self._theme

    def is_dirty(self) -> bool:
        return self._dirty

    def _refresh_name_label(self, name: str) -> None:
        self._name_label.setText(name)
        if name == DEFAULTS["name"]:
            self._name_label.setStyleSheet(
                "font-style: italic; color: #888; padding: 1px 4px;"
            )
        else:
            self._name_label.setStyleSheet(
                "font-weight: bold; color: #e8c84a;"
                " background: #2a2418; border: 1px solid #6a5420;"
                " border-radius: 4px; padding: 1px 6px;"
            )

    def _set_theme_dirty(self, dirty: bool) -> None:
        if dirty != self._dirty:
            self._dirty = dirty
            self.theme_dirty_changed.emit(dirty)

    # ──────────────────────────────────────────────────────────────────
    # UI construction
    # ──────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(6, 6, 6, 6)
        outer.setSpacing(6)

        # --- Top bar ---
        top = QHBoxLayout()
        top.setSpacing(4)

        self._name_label = QLabel()
        self._name_label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        top.addWidget(self._name_label)
        top.addStretch()

        load_btn = QPushButton("Load…")
        load_btn.setFixedWidth(52)
        load_btn.clicked.connect(self._on_load_clicked)
        top.addWidget(load_btn)

        save_btn = QPushButton("Save")
        save_btn.setFixedWidth(44)
        save_btn.clicked.connect(lambda: self.save_theme())
        top.addWidget(save_btn)

        reset_btn = QPushButton("Reset")
        reset_btn.setFixedWidth(48)
        reset_btn.clicked.connect(self._on_reset_clicked)
        top.addWidget(reset_btn)

        outer.addLayout(top)

        # --- Scroll area ---
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(scroll.Shape.NoFrame)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(2)

        content_layout.addWidget(self._build_background_section())
        content_layout.addWidget(self._build_text_section())
        content_layout.addWidget(self._build_active_section())
        content_layout.addWidget(self._build_inactive_section())
        content_layout.addWidget(self._build_layout_section())
        content_layout.addWidget(self._build_logo_section())
        content_layout.addStretch()

        scroll.setWidget(content)
        outer.addWidget(scroll, stretch=1)

    # ── Section builders ──────────────────────────────────────────────

    def _build_background_section(self) -> _CollapsibleSection:
        sec = _CollapsibleSection("Background")

        self._bg_color_btn = _ColorButton()
        self._bg_color_btn.color_changed.connect(self._on_bg_color_changed)
        sec.add_row("Color", self._bg_color_btn)

        self._overlay_slider = QSlider(Qt.Orientation.Horizontal)
        self._overlay_slider.setRange(0, 100)
        self._overlay_spin = QSpinBox()
        self._overlay_spin.setRange(0, 100)
        self._overlay_spin.setFixedWidth(52)
        self._overlay_spin.setSuffix("%")
        self._overlay_slider.valueChanged.connect(
            lambda v: self._sync_int(self._overlay_spin, v, self._on_overlay_opacity_changed)
        )
        self._overlay_spin.valueChanged.connect(
            lambda v: self._sync_int(self._overlay_slider, v, self._on_overlay_opacity_changed)
        )
        sec.add_row("Overlay %", self._overlay_slider, self._overlay_spin)

        self._overlay_color_btn = _ColorButton()
        self._overlay_color_btn.color_changed.connect(self._on_overlay_color_changed)
        sec.add_row("Overlay clr", self._overlay_color_btn)

        return sec

    def _build_text_section(self) -> _CollapsibleSection:
        sec = _CollapsibleSection("Text")

        self._text_color_btn = _ColorButton()
        self._text_color_btn.color_changed.connect(self._on_text_color_changed)
        sec.add_row("Color", self._text_color_btn)

        self._font_combo = QComboBox()
        self._font_combo.setMaxVisibleItems(12)
        self._font_combo.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        families = sorted(QFontDatabase.families())
        self._font_combo.addItems(families)
        self._font_combo.currentTextChanged.connect(self._on_font_family_changed)
        sec.add_row("Font", self._font_combo)

        self._font_size_slider = QSlider(Qt.Orientation.Horizontal)
        self._font_size_slider.setRange(24, 144)
        self._font_size_spin = QSpinBox()
        self._font_size_spin.setRange(24, 144)
        self._font_size_spin.setFixedWidth(52)
        self._font_size_spin.setSuffix("px")
        self._font_size_slider.valueChanged.connect(
            lambda v: self._sync_int(self._font_size_spin, v, self._on_font_size_changed)
        )
        self._font_size_spin.valueChanged.connect(
            lambda v: self._sync_int(self._font_size_slider, v, self._on_font_size_changed)
        )
        sec.add_row("Size", self._font_size_slider, self._font_size_spin)

        self._spacing_slider = QSlider(Qt.Orientation.Horizontal)
        self._spacing_slider.setRange(10, 30)  # ×0.1 → 1.0–3.0
        self._spacing_spin = QDoubleSpinBox()
        self._spacing_spin.setRange(1.0, 3.0)
        self._spacing_spin.setSingleStep(0.1)
        self._spacing_spin.setDecimals(1)
        self._spacing_spin.setFixedWidth(56)
        self._spacing_slider.valueChanged.connect(
            lambda v: self._sync_float(self._spacing_spin, v / 10.0, self._on_spacing_changed)
        )
        self._spacing_spin.valueChanged.connect(
            lambda v: self._sync_float(self._spacing_slider, round(v * 10), self._on_spacing_changed)
        )
        sec.add_row("Spacing", self._spacing_slider, self._spacing_spin)

        return sec

    def _build_active_section(self) -> _CollapsibleSection:
        sec = _CollapsibleSection("Active Line")

        self._active_color_btn = _ColorButton()
        self._active_color_btn.color_changed.connect(self._on_active_color_changed)
        sec.add_row("Fill clr", self._active_color_btn)

        self._active_bold_chk = QCheckBox("Bold")
        self._active_bold_chk.toggled.connect(self._on_active_bold_changed)
        sec.add_row("Style", self._active_bold_chk)

        self._active_glow_chk = QCheckBox("Glow")
        self._active_glow_chk.toggled.connect(self._on_active_glow_changed)
        sec.add_row("", self._active_glow_chk)

        self._glow_color_btn = _ColorButton()
        self._glow_color_btn.color_changed.connect(self._on_glow_color_changed)
        sec.add_row("Glow clr", self._glow_color_btn)

        # Stroke/outline
        self._active_stroke_color_btn = _ColorButton()
        self._active_stroke_color_btn.color_changed.connect(self._on_active_stroke_color_changed)
        sec.add_row("Outline clr", self._active_stroke_color_btn)

        self._active_stroke_width_spin = QSpinBox()
        self._active_stroke_width_spin.setRange(0, 40)
        self._active_stroke_width_spin.setFixedWidth(52)
        self._active_stroke_width_spin.setSuffix("px")
        self._active_stroke_width_spin.valueChanged.connect(self._on_active_stroke_width_changed)
        sec.add_row("Outline px", self._active_stroke_width_spin)

        # Per-active-line font override
        self._active_font_combo = QComboBox()
        self._active_font_combo.setMaxVisibleItems(12)
        self._active_font_combo.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self._active_font_combo.addItem("— inherit —")
        self._active_font_combo.addItems(sorted(QFontDatabase.families()))
        self._active_font_combo.currentTextChanged.connect(self._on_active_font_changed)
        sec.add_row("Font", self._active_font_combo)

        return sec

    def _build_inactive_section(self) -> _CollapsibleSection:
        sec = _CollapsibleSection("Inactive Lines")

        self._inactive_sliders: list[QSlider] = []
        self._inactive_spins: list[QDoubleSpinBox] = []

        for i, label in enumerate(("Line ±1", "Line ±2", "Line ±3")):
            sl = QSlider(Qt.Orientation.Horizontal)
            sl.setRange(0, 100)  # ×0.01 → 0.0–1.0
            sp = QDoubleSpinBox()
            sp.setRange(0.0, 1.0)
            sp.setSingleStep(0.01)
            sp.setDecimals(2)
            sp.setFixedWidth(60)

            idx = i  # capture

            def make_slider_handler(index: int, spin: QDoubleSpinBox):
                def handler(v: int):
                    self._sync_float(spin, v / 100.0, lambda val: self._on_inactive_changed(index, val))
                return handler

            def make_spin_handler(index: int, slider: QSlider):
                def handler(v: float):
                    self._sync_float(slider, round(v * 100), lambda val: self._on_inactive_changed(index, val))
                return handler

            sl.valueChanged.connect(make_slider_handler(idx, sp))
            sp.valueChanged.connect(make_spin_handler(idx, sl))

            self._inactive_sliders.append(sl)
            self._inactive_spins.append(sp)
            sec.add_row(label, sl, sp)

        return sec

    def _build_layout_section(self) -> _CollapsibleSection:
        sec = _CollapsibleSection("Layout")

        self._position_combo = QComboBox()
        self._position_combo.addItems(["left", "center", "right"])
        self._position_combo.currentTextChanged.connect(self._on_position_changed)
        sec.add_row("Position", self._position_combo)

        self._highlight_combo = QComboBox()
        self._highlight_combo.addItems(["line", "word", "character"])
        self._highlight_combo.currentTextChanged.connect(self._on_highlight_changed)
        sec.add_row("Highlight", self._highlight_combo)

        self._col_width_slider = QSlider(Qt.Orientation.Horizontal)
        self._col_width_slider.setRange(200, 1920)
        self._col_width_slider.setSingleStep(10)
        self._col_width_slider.setPageStep(100)
        self._col_width_spin = QSpinBox()
        self._col_width_spin.setRange(200, 1920)
        self._col_width_spin.setSingleStep(10)
        self._col_width_spin.setFixedWidth(64)
        self._col_width_spin.setSuffix("px")
        self._col_width_slider.valueChanged.connect(
            lambda v: self._sync_int(self._col_width_spin, v, self._on_col_width_changed)
        )
        self._col_width_spin.valueChanged.connect(
            lambda v: self._sync_int(self._col_width_slider, v, self._on_col_width_changed)
        )
        sec.add_row("Col width", self._col_width_slider, self._col_width_spin)

        return sec

    def _build_logo_section(self) -> _CollapsibleSection:
        sec = _CollapsibleSection("Intro Logo")

        # File picker row — wrap in a container widget so add_row accepts it
        self._logo_path_label = QLabel("(none)")
        self._logo_path_label.setWordWrap(False)
        self._logo_browse_btn = QPushButton("Browse…")
        self._logo_browse_btn.setFixedWidth(64)
        self._logo_browse_btn.clicked.connect(self._on_logo_browse)
        self._logo_clear_btn = QPushButton("Clear")
        self._logo_clear_btn.setFixedWidth(44)
        self._logo_clear_btn.clicked.connect(self._on_logo_clear)
        path_widget = QWidget()
        path_layout = QHBoxLayout(path_widget)
        path_layout.setContentsMargins(0, 0, 0, 0)
        path_layout.setSpacing(4)
        path_layout.addWidget(self._logo_path_label, stretch=1)
        path_layout.addWidget(self._logo_browse_btn)
        path_layout.addWidget(self._logo_clear_btn)
        sec.add_row("File", path_widget)

        # Width slider + spinbox
        self._logo_width_slider = QSlider(Qt.Orientation.Horizontal)
        self._logo_width_slider.setRange(50, 1920)
        self._logo_width_slider.setSingleStep(10)
        self._logo_width_slider.setPageStep(50)
        self._logo_width_spin = QSpinBox()
        self._logo_width_spin.setRange(50, 1920)
        self._logo_width_spin.setSingleStep(10)
        self._logo_width_spin.setFixedWidth(64)
        self._logo_width_spin.setSuffix("px")
        self._logo_width_slider.valueChanged.connect(
            lambda v: self._sync_int(self._logo_width_spin, v, self._on_logo_width_changed)
        )
        self._logo_width_spin.valueChanged.connect(
            lambda v: self._sync_int(self._logo_width_slider, v, self._on_logo_width_changed)
        )
        sec.add_row("Width", self._logo_width_slider, self._logo_width_spin)

        # Alignment combo
        self._logo_align_combo = QComboBox()
        self._logo_align_combo.addItems(["left", "center", "right"])
        self._logo_align_combo.currentTextChanged.connect(self._on_logo_align_changed)
        sec.add_row("Align", self._logo_align_combo)

        return sec

    # ──────────────────────────────────────────────────────────────────
    # Populate controls from self._theme
    # ──────────────────────────────────────────────────────────────────

    def _populate_controls(self) -> None:
        self._blocking = True
        t = self._theme
        try:
            self._refresh_name_label(t.name)

            # Background
            self._bg_color_btn.set_color(t.background_color)
            self._overlay_slider.setValue(t.text_overlay_opacity)
            self._overlay_spin.setValue(t.text_overlay_opacity)
            self._overlay_color_btn.set_color(t.text_overlay_color)

            # Text
            self._text_color_btn.set_color(t.text_color)
            idx = self._font_combo.findText(t.font_family)
            if idx >= 0:
                self._font_combo.setCurrentIndex(idx)
            self._font_size_slider.setValue(t.font_size)
            self._font_size_spin.setValue(t.font_size)
            self._spacing_slider.setValue(round(t.line_spacing * 10))
            self._spacing_spin.setValue(t.line_spacing)

            # Active line
            active_color = t.active_text_color or t.text_color
            self._active_color_btn.set_color(active_color)
            self._active_bold_chk.setChecked(t.active_text_bold)
            self._active_glow_chk.setChecked(t.active_text_glow)
            glow_color = t.active_glow_color or active_color
            self._glow_color_btn.set_color(glow_color)
            self._glow_color_btn.setEnabled(t.active_text_glow)
            self._active_stroke_color_btn.set_color(t.active_text_stroke_color)
            self._active_stroke_width_spin.setValue(t.active_text_stroke_width)
            if t.active_font_family:
                idx = self._active_font_combo.findText(t.active_font_family)
                self._active_font_combo.setCurrentIndex(idx if idx >= 0 else 0)
            else:
                self._active_font_combo.setCurrentIndex(0)  # "— inherit —"

            # Inactive lines
            grad = t.inactive_text_opacity_gradient
            for i, (sl, sp) in enumerate(zip(self._inactive_sliders, self._inactive_spins)):
                val = grad[i] if i < len(grad) else 0.0
                sl.setValue(round(val * 100))
                sp.setValue(val)

            # Layout
            pos_idx = self._position_combo.findText(t.lyric_position)
            if pos_idx >= 0:
                self._position_combo.setCurrentIndex(pos_idx)
            hl_idx = self._highlight_combo.findText(t.highlight_mode)
            if hl_idx >= 0:
                self._highlight_combo.setCurrentIndex(hl_idx)
            self._col_width_slider.setValue(t.column_width)
            self._col_width_spin.setValue(t.column_width)

            # Intro Logo
            p = t.logo_path
            self._logo_path_label.setText(Path(p).name if p else "(none)")
            self._logo_width_slider.setValue(t.logo_width)
            self._logo_width_spin.setValue(t.logo_width)
            idx = self._logo_align_combo.findText(t.logo_h_align)
            if idx >= 0:
                self._logo_align_combo.setCurrentIndex(idx)

        finally:
            self._blocking = False

        self._set_theme_dirty(False)

    # ──────────────────────────────────────────────────────────────────
    # Sync helpers (prevent double-fire between slider and spinbox)
    # ──────────────────────────────────────────────────────────────────

    def _sync_int(self, target: QSpinBox | QSlider, value: int, callback) -> None:
        if self._blocking:
            return
        self._blocking = True
        try:
            target.setValue(value)
        finally:
            self._blocking = False
        callback(value)

    def _sync_float(self, target: QDoubleSpinBox | QSlider, value: float, callback) -> None:
        if self._blocking:
            return
        self._blocking = True
        try:
            target.setValue(value)
        finally:
            self._blocking = False
        callback(value)

    # ──────────────────────────────────────────────────────────────────
    # Change handlers
    # ──────────────────────────────────────────────────────────────────

    def _on_bg_color_changed(self, hex_str: str) -> None:
        self._theme.background_color = hex_str
        self._set_theme_dirty(True)
        self.theme_changed.emit(self._theme)

    def _on_overlay_opacity_changed(self, value: int) -> None:
        self._theme.text_overlay_opacity = int(value)
        self._set_theme_dirty(True)
        self.theme_changed.emit(self._theme)

    def _on_overlay_color_changed(self, hex_str: str) -> None:
        self._theme.text_overlay_color = hex_str
        self._set_theme_dirty(True)
        self.theme_changed.emit(self._theme)

    def _on_text_color_changed(self, hex_str: str) -> None:
        self._theme.text_color = hex_str
        self._set_theme_dirty(True)
        self.theme_changed.emit(self._theme)

    def _on_font_family_changed(self, family: str) -> None:
        if self._blocking:
            return
        self._theme.font_family = family
        self._set_theme_dirty(True)
        self.theme_changed.emit(self._theme)

    def _on_font_size_changed(self, value: int) -> None:
        self._theme.font_size = int(value)
        self._set_theme_dirty(True)
        self.theme_changed.emit(self._theme)

    def _on_spacing_changed(self, value: float) -> None:
        self._theme.line_spacing = round(float(value), 1)
        self._set_theme_dirty(True)
        self.theme_changed.emit(self._theme)

    def _on_active_color_changed(self, hex_str: str) -> None:
        self._theme.active_text_color = hex_str
        self._set_theme_dirty(True)
        self.theme_changed.emit(self._theme)

    def _on_active_bold_changed(self, checked: bool) -> None:
        if self._blocking:
            return
        self._theme.active_text_bold = checked
        self._set_theme_dirty(True)
        self.theme_changed.emit(self._theme)

    def _on_active_glow_changed(self, checked: bool) -> None:
        if self._blocking:
            return
        self._glow_color_btn.setEnabled(checked)
        self._theme.active_text_glow = checked
        self._set_theme_dirty(True)
        self.theme_changed.emit(self._theme)

    def _on_glow_color_changed(self, hex_str: str) -> None:
        self._theme.active_glow_color = hex_str
        self._set_theme_dirty(True)
        self.theme_changed.emit(self._theme)

    def _on_active_stroke_color_changed(self, hex_str: str) -> None:
        self._theme.active_text_stroke_color = hex_str
        self._set_theme_dirty(True)
        self.theme_changed.emit(self._theme)

    def _on_active_stroke_width_changed(self, value: int) -> None:
        if self._blocking:
            return
        self._theme.active_text_stroke_width = int(value)
        self._set_theme_dirty(True)
        self.theme_changed.emit(self._theme)

    def _on_active_font_changed(self, text: str) -> None:
        if self._blocking:
            return
        self._theme.active_font_family = None if text == "— inherit —" else text
        self._set_theme_dirty(True)
        self.theme_changed.emit(self._theme)

    def _on_inactive_changed(self, index: int, value: float) -> None:
        grad = self._theme.inactive_text_opacity_gradient
        while len(grad) <= index:
            grad.append(0.0)
        grad[index] = round(float(value), 2)
        self._set_theme_dirty(True)
        self.theme_changed.emit(self._theme)

    def _on_position_changed(self, value: str) -> None:
        if self._blocking:
            return
        self._theme.lyric_position = value
        self._set_theme_dirty(True)
        self.theme_changed.emit(self._theme)

    def _on_highlight_changed(self, value: str) -> None:
        if self._blocking:
            return
        self._theme.highlight_mode = value
        self._set_theme_dirty(True)
        self.theme_changed.emit(self._theme)

    def _on_col_width_changed(self, value: int) -> None:
        self._theme.column_width = int(value)
        self._set_theme_dirty(True)
        self.theme_changed.emit(self._theme)

    def _on_logo_browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Logo Image", "", "Images (*.png *.jpg *.jpeg *.webp)"
        )
        if path:
            self._theme.logo_path = path
            self._logo_path_label.setText(Path(path).name)
            self._set_theme_dirty(True)
            self.theme_changed.emit(self._theme)

    def _on_logo_clear(self) -> None:
        self._theme.logo_path = ""
        self._logo_path_label.setText("(none)")
        self._set_theme_dirty(True)
        self.theme_changed.emit(self._theme)

    def _on_logo_width_changed(self, value: int) -> None:
        self._theme.logo_width = int(value)
        self._set_theme_dirty(True)
        self.theme_changed.emit(self._theme)

    def _on_logo_align_changed(self, value: str) -> None:
        if self._blocking:
            return
        self._theme.logo_h_align = value
        self._set_theme_dirty(True)
        self.theme_changed.emit(self._theme)

    # ──────────────────────────────────────────────────────────────────
    # Button handlers
    # ──────────────────────────────────────────────────────────────────

    def _on_load_clicked(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Theme", "themes/", "JSON (*.json)"
        )
        if path:
            self.load_theme_file(path)

    def _on_reset_clicked(self) -> None:
        self._theme = load_theme()
        self._filepath = None
        self._populate_controls()
        self._set_theme_dirty(True)
        self.theme_changed.emit(self._theme)
