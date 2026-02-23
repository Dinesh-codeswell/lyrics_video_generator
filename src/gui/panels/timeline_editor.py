"""Visual timeline editor panel for adjusting lyric timestamps."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from PyQt6.QtCore import QEvent, QObject, QPoint, Qt, pyqtSignal
from PyQt6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QPainter,
    QPen,
    QPolygon,
    QWheelEvent,
)
from PyQt6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from src.gui.audio_player import AudioPlayer

# ──────────────────────────────────────────────────────────────────────────────
# Internal data model
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class _Marker:
    """Mutable representation of a single timed lyric entry."""
    start_time: float   # seconds
    text: str


# ──────────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────────

BASE_PX_PER_SEC = 100.0   # pixels per second at zoom 1.0
RULER_H         = 28      # ruler strip height in px
TRACK_H         = 120     # track area height in px
CANVAS_H        = RULER_H + TRACK_H
HIT_RADIUS      = 8       # px — marker click detection half-width
MIN_GAP_S       = 0.05    # minimum seconds between adjacent markers
SNAP_STEP_S     = 0.1     # snap-grid resolution in seconds


# ──────────────────────────────────────────────────────────────────────────────
# Helper
# ──────────────────────────────────────────────────────────────────────────────

def _fmt_s(t: float) -> str:
    """Format seconds as M:SS."""
    s = int(t)
    return f"{s // 60}:{s % 60:02d}"


# ──────────────────────────────────────────────────────────────────────────────
# Timeline canvas  (inner widget inside QScrollArea)
# ──────────────────────────────────────────────────────────────────────────────

class _TimelineCanvas(QWidget):
    """Custom QPainter widget: ruler, lyric-marker track, playback cursor."""

    marker_moved    = pyqtSignal(int, float)  # index, new_start_time_s
    marker_selected = pyqtSignal(int)          # index (-1 = deselected)
    seek_requested  = pyqtSignal(float)        # time_s

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setFixedHeight(CANVAS_H)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setMouseTracking(True)

        self._markers: list[_Marker] = []
        self._duration_s: float = 0.0
        self._px_per_sec: float = BASE_PX_PER_SEC
        self._cursor_s: float = 0.0
        self._selected: int = -1
        self._active: int = -1       # line currently "playing through"
        self._dragging: int = -1     # marker index being dragged
        self._drag_offset_px: float = 0.0
        self._snap: bool = True

        self._update_width()

    # ── public API ────────────────────────────────────────────────────────────

    def load(self, markers: list[_Marker], duration_s: float) -> None:
        self._markers = markers
        self._duration_s = duration_s
        self._update_active_marker()
        self._update_width()
        self.update()

    def set_px_per_sec(self, pps: float) -> None:
        self._px_per_sec = pps
        self._update_width()
        self.update()

    def set_cursor(self, time_s: float) -> None:
        self._cursor_s = time_s
        self._update_active_marker()
        self.update()

    def set_selected(self, index: int) -> None:
        self._selected = index
        self.update()

    def set_snap(self, enabled: bool) -> None:
        self._snap = enabled

    # ── sizing ────────────────────────────────────────────────────────────────

    def _update_width(self) -> None:
        w = max(200, int(self._duration_s * self._px_per_sec) + 60)
        self.setFixedWidth(w)

    # ── coordinate helpers ────────────────────────────────────────────────────

    def _time_to_x(self, t: float) -> int:
        return int(t * self._px_per_sec)

    def _x_to_time(self, x: float) -> float:
        return x / self._px_per_sec

    # ── active marker ─────────────────────────────────────────────────────────

    def _update_active_marker(self) -> None:
        active = -1
        for i, m in enumerate(self._markers):
            end_t = (
                self._markers[i + 1].start_time
                if i + 1 < len(self._markers)
                else self._duration_s
            )
            if m.start_time <= self._cursor_s < end_t:
                active = i
                break
        self._active = active

    # ── paint ─────────────────────────────────────────────────────────────────

    def paintEvent(self, _event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        self._paint_ruler(p)
        self._paint_track(p)
        self._paint_markers(p)
        self._paint_cursor(p)
        p.end()

    def _paint_ruler(self, p: QPainter) -> None:
        w = self.width()
        p.fillRect(0, 0, w, RULER_H, QColor("#2b2b2b"))

        font = QFont()
        font.setPointSize(8)
        p.setFont(font)
        fm = QFontMetrics(font)

        major_s, minor_s = self._tick_granularity()

        # Minor ticks
        t = 0.0
        while t <= self._duration_s + minor_s:
            x = self._time_to_x(t)
            p.setPen(QPen(QColor("#555555"), 1))
            p.drawLine(x, RULER_H - 5, x, RULER_H)
            t = round(t + minor_s, 6)

        # Major ticks + labels
        t = 0.0
        while t <= self._duration_s + major_s:
            x = self._time_to_x(t)
            p.setPen(QPen(QColor("#888888"), 1))
            p.drawLine(x, RULER_H - 12, x, RULER_H)
            label = _fmt_s(t)
            lw = fm.horizontalAdvance(label)
            p.setPen(QColor("#cccccc"))
            p.drawText(x - lw // 2, RULER_H - 14, label)
            t = round(t + major_s, 6)

    def _paint_track(self, p: QPainter) -> None:
        w = self.width()
        p.fillRect(0, RULER_H, w, TRACK_H, QColor("#1e1e1e"))

        for i, m in enumerate(self._markers):
            x1 = self._time_to_x(m.start_time)
            end_t = (
                self._markers[i + 1].start_time
                if i + 1 < len(self._markers)
                else self._duration_s
            )
            x2 = self._time_to_x(end_t)
            if i == self._active:
                color = QColor("#1a3a1a")
            elif i % 2 == 0:
                color = QColor("#252525")
            else:
                color = QColor("#222222")
            p.fillRect(x1, RULER_H, x2 - x1, TRACK_H, color)

    def _paint_markers(self, p: QPainter) -> None:
        font = QFont()
        font.setPointSize(8)
        p.setFont(font)
        fm = QFontMetrics(font)
        max_label_w = 110

        for i, m in enumerate(self._markers):
            x = self._time_to_x(m.start_time)
            is_sel    = (i == self._selected)
            is_active = (i == self._active)

            if is_sel:
                color = QColor("#ffcc44")
            elif is_active:
                color = QColor("#66dd66")
            else:
                color = QColor("#5588bb")

            # Vertical line
            p.setPen(QPen(color, 2 if is_sel else 1))
            p.drawLine(x, RULER_H, x, CANVAS_H)

            # Triangle handle
            h = 7
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(color)
            p.drawPolygon(QPolygon([
                QPoint(x,     RULER_H + h * 2),
                QPoint(x - h, RULER_H),
                QPoint(x + h, RULER_H),
            ]))

            # Text label
            label = m.text
            while fm.horizontalAdvance(label) > max_label_w and label:
                label = label[:-1]
            if label != m.text:
                label = label[:-1] + "…"
            p.setPen(color)
            p.drawText(x + 5, RULER_H + fm.ascent() + 6, label)

    def _paint_cursor(self, p: QPainter) -> None:
        if self._duration_s <= 0:
            return
        x = self._time_to_x(self._cursor_s)
        p.setPen(QPen(QColor("#ff4444"), 1))
        p.drawLine(x, 0, x, CANVAS_H)

    # ── adaptive tick granularity ─────────────────────────────────────────────

    def _tick_granularity(self) -> tuple[float, float]:
        pps = self._px_per_sec
        if pps >= 500:
            return 1.0, 0.1
        if pps >= 150:
            return 5.0, 1.0
        if pps >= 50:
            return 10.0, 2.0
        if pps >= 15:
            return 30.0, 10.0
        return 60.0, 30.0

    # ── mouse ─────────────────────────────────────────────────────────────────

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() != Qt.MouseButton.LeftButton:
            return
        x = event.position().x()
        hit = self._find_marker_at(x)
        if hit >= 0:
            self._dragging = hit
            self._drag_offset_px = x - self._time_to_x(self._markers[hit].start_time)
            self.marker_selected.emit(hit)
        else:
            t = max(0.0, min(self._duration_s, self._x_to_time(x)))
            self.seek_requested.emit(t)
            self.marker_selected.emit(-1)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._dragging < 0:
            return
        x = event.position().x() - self._drag_offset_px
        new_t = self._x_to_time(x)

        i = self._dragging
        min_t = self._markers[i - 1].start_time + MIN_GAP_S if i > 0 else 0.0
        max_t = (
            self._markers[i + 1].start_time - MIN_GAP_S
            if i + 1 < len(self._markers)
            else self._duration_s
        )
        new_t = max(min_t, min(max_t, new_t))
        if self._snap:
            new_t = round(new_t / SNAP_STEP_S) * SNAP_STEP_S

        self._markers[i].start_time = new_t
        self.marker_moved.emit(i, new_t)
        self.update()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        self._dragging = -1

    def _find_marker_at(self, x: float) -> int:
        best, best_d = -1, HIT_RADIUS + 1
        for i, m in enumerate(self._markers):
            d = abs(x - self._time_to_x(m.start_time))
            if d < best_d:
                best_d, best = d, i
        return best


# ──────────────────────────────────────────────────────────────────────────────
# Marker detail / edit area
# ──────────────────────────────────────────────────────────────────────────────

class _MarkerDetailArea(QWidget):
    """Edit strip below the timeline canvas for the selected marker."""

    text_changed = pyqtSignal(int, str)    # index, new_text
    time_changed = pyqtSignal(int, float)  # index, new_start_time_s
    prev_clicked = pyqtSignal()
    next_clicked = pyqtSignal()
    save_clicked = pyqtSignal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._index: int = -1
        self._blocking: bool = False
        self._build_ui()

    def _build_ui(self) -> None:
        row = QHBoxLayout(self)
        row.setContentsMargins(6, 4, 6, 4)
        row.setSpacing(8)

        self._prev_btn = QPushButton("◀ Prev")
        self._prev_btn.setFixedWidth(70)
        self._prev_btn.clicked.connect(self.prev_clicked)
        row.addWidget(self._prev_btn)

        self._text_edit = QLineEdit()
        self._text_edit.setPlaceholderText("Select a marker to edit")
        self._text_edit.textEdited.connect(self._on_text_edited)
        row.addWidget(self._text_edit, stretch=2)

        row.addWidget(QLabel("Start:"))
        self._start_spin = QDoubleSpinBox()
        self._start_spin.setRange(0.0, 9999.0)
        self._start_spin.setDecimals(2)
        self._start_spin.setSingleStep(0.1)
        self._start_spin.setSuffix(" s")
        self._start_spin.setFixedWidth(90)
        self._start_spin.valueChanged.connect(self._on_start_changed)
        row.addWidget(self._start_spin)

        row.addWidget(QLabel("End:"))
        self._end_lbl = QLabel("—")
        self._end_lbl.setFixedWidth(58)
        row.addWidget(self._end_lbl)

        row.addWidget(QLabel("Dur:"))
        self._dur_lbl = QLabel("—")
        self._dur_lbl.setFixedWidth(58)
        row.addWidget(self._dur_lbl)

        self._dirty_lbl = QLabel("")
        self._dirty_lbl.setStyleSheet("color: #ff8800; font-weight: bold;")
        self._dirty_lbl.setFixedWidth(90)
        row.addWidget(self._dirty_lbl)

        self._save_btn = QPushButton("Save")
        self._save_btn.setFixedWidth(60)
        self._save_btn.clicked.connect(self.save_clicked)
        row.addWidget(self._save_btn)

        self._next_btn = QPushButton("Next ▶")
        self._next_btn.setFixedWidth(70)
        self._next_btn.clicked.connect(self.next_clicked)
        row.addWidget(self._next_btn)

        self._set_enabled(False)

    # ── public API ────────────────────────────────────────────────────────────

    def load(self, index: int, markers: list[_Marker], duration_s: float) -> None:
        self._blocking = True
        self._index = index

        if index < 0 or index >= len(markers):
            self._set_enabled(False)
            self._blocking = False
            return

        self._set_enabled(True)
        m = markers[index]
        self._text_edit.setText(m.text)
        self._start_spin.setValue(m.start_time)

        end_t = markers[index + 1].start_time if index + 1 < len(markers) else duration_s
        dur   = end_t - m.start_time
        self._end_lbl.setText(f"{end_t:.2f} s")
        self._dur_lbl.setText(f"{dur:.2f} s")

        self._prev_btn.setEnabled(index > 0)
        self._next_btn.setEnabled(index < len(markers) - 1)
        self._blocking = False

    def set_dirty(self, dirty: bool) -> None:
        self._dirty_lbl.setText("● Unsaved" if dirty else "")

    # ── internals ────────────────────────────────────────────────────────────

    def _set_enabled(self, enabled: bool) -> None:
        self._text_edit.setEnabled(enabled)
        self._start_spin.setEnabled(enabled)
        if not enabled:
            self._text_edit.clear()
            self._start_spin.setValue(0.0)
            self._end_lbl.setText("—")
            self._dur_lbl.setText("—")
            self._prev_btn.setEnabled(False)
            self._next_btn.setEnabled(False)

    def _on_text_edited(self, text: str) -> None:
        if not self._blocking and self._index >= 0:
            self.text_changed.emit(self._index, text)

    def _on_start_changed(self, value: float) -> None:
        if not self._blocking and self._index >= 0:
            self.time_changed.emit(self._index, value)


# ──────────────────────────────────────────────────────────────────────────────
# Top-level panel (public API)
# ──────────────────────────────────────────────────────────────────────────────

class TimelineEditorPanel(QGroupBox):
    """Timeline editor panel — center-bottom area of the main window.

    Pass the shared AudioPlayer on construction; call load_song(paths) when a
    song is selected (paths is the dict emitted by SongSelectorPanel.song_loaded).
    """

    lyrics_modified = pyqtSignal()   # emitted when unsaved edits exist

    def __init__(self, audio_player: AudioPlayer, parent: QWidget | None = None):
        super().__init__("Timeline Editor", parent)
        self._player       = audio_player
        self._markers:     list[_Marker] = []
        self._duration_s:  float = 0.0
        self._end_marker_t: float = 0.0   # original/saved end marker time
        self._lyrics_path: str | None = None
        self._dirty        = False
        self._zoom         = 1.0           # multiplier on BASE_PX_PER_SEC

        self._build_ui()
        self._connect_player()

    # ── public API ────────────────────────────────────────────────────────────

    def load_song(self, paths: dict) -> None:
        """Load lyrics from the paths dict emitted by SongSelectorPanel."""
        lyrics_path = paths.get("lyrics")
        if not lyrics_path:
            return

        from src.core.lyrics_parser import parse_lyrics
        try:
            data = parse_lyrics(lyrics_path)
        except Exception as exc:
            QMessageBox.critical(self, "Timeline Load Error", str(exc))
            return

        self._lyrics_path   = lyrics_path
        self._end_marker_t  = data["lines"][-1].end_time if data["lines"] else 0.0
        self._markers       = [
            _Marker(start_time=line.start_time, text=line.text)
            for line in data["lines"]
        ]
        self._dirty = False

        self._canvas.load(self._markers, self._duration_s)
        self._detail.load(-1, self._markers, self._duration_s)
        self._detail.set_dirty(False)
        self.setTitle(f"Timeline Editor — {data['title']}")

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Canvas (must exist before toolbar connects snap checkbox)
        self._canvas = _TimelineCanvas()
        self._canvas.marker_moved.connect(self._on_marker_moved)
        self._canvas.marker_selected.connect(self._on_marker_selected)
        self._canvas.seek_requested.connect(self._on_seek_requested)

        layout.addLayout(self._build_toolbar())

        self._scroll = QScrollArea()
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setWidgetResizable(False)
        self._scroll.setWidget(self._canvas)
        self._scroll.setMinimumHeight(CANVAS_H + 22)
        # Intercept Ctrl+scroll on the viewport for zoom
        self._scroll.viewport().installEventFilter(self)
        layout.addWidget(self._scroll, stretch=1)

        self._detail = _MarkerDetailArea()
        self._detail.text_changed.connect(self._on_text_changed)
        self._detail.time_changed.connect(self._on_time_changed)
        self._detail.prev_clicked.connect(self._on_prev)
        self._detail.next_clicked.connect(self._on_next)
        self._detail.save_clicked.connect(self._on_save)
        layout.addWidget(self._detail)

    def _build_toolbar(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(8)

        row.addWidget(QLabel("Zoom:"))

        self._zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self._zoom_slider.setRange(1, 40)    # slider value / 10 = zoom multiplier
        self._zoom_slider.setValue(10)        # 1.0×
        self._zoom_slider.setFixedWidth(140)
        self._zoom_slider.setToolTip("Zoom timeline (Ctrl+scroll also works)")
        self._zoom_slider.valueChanged.connect(self._on_zoom_slider_changed)
        row.addWidget(self._zoom_slider)

        self._zoom_lbl = QLabel("1.0×")
        self._zoom_lbl.setFixedWidth(36)
        row.addWidget(self._zoom_lbl)

        self._snap_cb = QCheckBox("Snap 0.1s")
        self._snap_cb.setChecked(True)
        self._snap_cb.toggled.connect(self._canvas.set_snap)
        row.addWidget(self._snap_cb)

        row.addStretch()
        return row

    # ── AudioPlayer connection ────────────────────────────────────────────────

    def _connect_player(self) -> None:
        self._player.position_changed.connect(self._on_position_changed)
        self._player.duration_changed.connect(self._on_duration_changed)

    def _on_position_changed(self, ms: int) -> None:
        t = ms / 1000.0
        self._canvas.set_cursor(t)
        if self._player.is_playing:
            self._auto_scroll(t)

    def _on_duration_changed(self, ms: int) -> None:
        self._duration_s = ms / 1000.0
        self._canvas.load(self._markers, self._duration_s)

    # ── auto-scroll ───────────────────────────────────────────────────────────

    def _auto_scroll(self, time_s: float) -> None:
        cursor_x  = int(time_s * self._px_per_sec())
        sb        = self._scroll.horizontalScrollBar()
        vp_w      = self._scroll.viewport().width()
        left, right = sb.value(), sb.value() + vp_w
        # Re-centre when cursor leaves the middle 50% of the viewport
        if cursor_x < left + vp_w * 0.25 or cursor_x > right - vp_w * 0.25:
            sb.setValue(max(0, cursor_x - vp_w // 2))

    # ── zoom ──────────────────────────────────────────────────────────────────

    def _px_per_sec(self) -> float:
        return BASE_PX_PER_SEC * self._zoom

    def _on_zoom_slider_changed(self, value: int) -> None:
        self._zoom = value / 10.0
        self._zoom_lbl.setText(f"{self._zoom:.1f}×")
        self._canvas.set_px_per_sec(self._px_per_sec())

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:  # noqa: N802
        if obj is self._scroll.viewport() and event.type() == QEvent.Type.Wheel:
            wheel: QWheelEvent = event  # type: ignore[assignment]
            if wheel.modifiers() & Qt.KeyboardModifier.ControlModifier:
                step = 1 if wheel.angleDelta().y() > 0 else -1
                self._zoom_slider.setValue(
                    max(1, min(40, self._zoom_slider.value() + step))
                )
                return True   # consume — don't scroll the scrollbar
        return super().eventFilter(obj, event)

    # ── marker canvas signals ─────────────────────────────────────────────────

    def _on_marker_moved(self, index: int, new_time: float) -> None:
        self._mark_dirty()
        self._detail.load(index, self._markers, self._duration_s)

    def _on_marker_selected(self, index: int) -> None:
        self._canvas.set_selected(index)
        self._detail.load(index, self._markers, self._duration_s)

    def _on_seek_requested(self, time_s: float) -> None:
        self._player.seek(int(time_s * 1000))

    # ── detail area signals ───────────────────────────────────────────────────

    def _on_text_changed(self, index: int, text: str) -> None:
        if 0 <= index < len(self._markers):
            self._markers[index].text = text
            self._canvas.update()
            self._mark_dirty()

    def _on_time_changed(self, index: int, new_t: float) -> None:
        if 0 <= index < len(self._markers):
            i = index
            min_t = self._markers[i - 1].start_time + MIN_GAP_S if i > 0 else 0.0
            max_t = (
                self._markers[i + 1].start_time - MIN_GAP_S
                if i + 1 < len(self._markers)
                else self._duration_s
            )
            new_t = max(min_t, min(max_t, new_t))
            self._markers[i].start_time = new_t
            self._canvas.load(self._markers, self._duration_s)
            self._canvas.set_selected(i)
            self._detail.load(i, self._markers, self._duration_s)
            self._mark_dirty()

    def _on_prev(self) -> None:
        idx = self._canvas._selected
        if idx > 0:
            self._on_marker_selected(idx - 1)

    def _on_next(self) -> None:
        idx = self._canvas._selected
        if 0 <= idx < len(self._markers) - 1:
            self._on_marker_selected(idx + 1)

    # ── save ──────────────────────────────────────────────────────────────────

    def _on_save(self) -> None:
        if not self._lyrics_path:
            return
        try:
            self._write_lyrics(self._lyrics_path)
        except Exception as exc:
            QMessageBox.critical(self, "Save Error", str(exc))
            return
        self._dirty = False
        self._detail.set_dirty(False)

    def _write_lyrics(self, path: str) -> None:
        filepath = Path(path)
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        raw_lyrics = [
            {"time": round(m.start_time, 3), "text": m.text}
            for m in self._markers
        ]
        # End marker: use audio duration when known, else preserved original
        end_t = self._duration_s if self._duration_s > 0 else self._end_marker_t
        raw_lyrics.append({"time": round(end_t, 3), "text": ""})
        data["lyrics"] = raw_lyrics

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    # ── dirty tracking ────────────────────────────────────────────────────────

    def _mark_dirty(self) -> None:
        if not self._dirty:
            self._dirty = True
            self._detail.set_dirty(True)
            self.lyrics_modified.emit()
