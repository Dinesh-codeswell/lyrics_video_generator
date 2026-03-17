"""Visual timeline editor panel for adjusting lyric timestamps."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from PyQt6.QtCore import QEvent, QObject, QPoint, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QPainter,
    QPen,
    QPolygon,
    QUndoCommand,
    QUndoStack,
    QWheelEvent,
)
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
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
    QSpinBox,
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
# Beat-grid helpers
# ──────────────────────────────────────────────────────────────────────────────

def _seconds_to_beats(t_s: float, bpm: float, offset_s: float = 0.0) -> float:
    """Convert a time in seconds to a beat position (fractional beats from beat 1)."""
    return (t_s - offset_s) * bpm / 60.0


def _beats_to_seconds(beat: float, bpm: float, offset_s: float = 0.0) -> float:
    """Convert a beat position to seconds."""
    return beat * 60.0 / bpm + offset_s


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

    marker_moved          = pyqtSignal(int, float)         # index, new_start_time_s
    marker_drag_committed = pyqtSignal(int, float, float)  # index, old_t, new_t
    marker_selected       = pyqtSignal(int)                # index (-1 = deselected)
    seek_requested        = pyqtSignal(float)              # time_s
    intro_marker_moved    = pyqtSignal(float)              # new_time_s (live during drag)
    outro_marker_moved    = pyqtSignal(float)              # new_time_s (live during drag)

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
        self._dragging: int = -1        # marker index being dragged
        self._drag_offset_px: float = 0.0
        self._drag_start_time: float = 0.0  # time at start of drag (for undo)
        self._snap: bool = True
        self._intro_end_t: float | None = None
        self._dragging_intro: bool = False
        self._outro_start_t: float | None = None
        self._dragging_outro: bool = False

        # Beat mode state
        self._beat_mode: bool = False
        self._bpm: float = 120.0
        self._time_sig_num: int = 4
        self._beat_offset_s: float = 0.0
        self._snap_subdivision: float = 0.25  # fraction of a beat (default: 1/4)

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

    def set_beat_params(
        self,
        beat_mode: bool,
        bpm: float,
        time_sig_num: int,
        offset_s: float,
        snap_subdivision: float,
    ) -> None:
        self._beat_mode = beat_mode
        self._bpm = bpm
        self._time_sig_num = time_sig_num
        self._beat_offset_s = offset_s
        self._snap_subdivision = snap_subdivision
        self.update()

    def _snap_time(self, t: float) -> float:
        """Snap a time value to the current grid (beat subdivision or 0.1s)."""
        if self._beat_mode and self._bpm > 0 and self._snap_subdivision > 0:
            b = _seconds_to_beats(t, self._bpm, self._beat_offset_s)
            b = round(b / self._snap_subdivision) * self._snap_subdivision
            return _beats_to_seconds(b, self._bpm, self._beat_offset_s)
        return round(t / SNAP_STEP_S) * SNAP_STEP_S

    def set_intro_marker(self, t: float | None) -> None:
        self._intro_end_t = t
        self.update()

    def set_outro_marker(self, t: float | None) -> None:
        self._outro_start_t = t
        self.update()

    # ── sizing ────────────────────────────────────────────────────────────────

    def _update_width(self) -> None:
        w = max(200, int(self._duration_s * self._px_per_sec) + 60)
        self.setFixedWidth(w)

    # ── coordinate helpers ────────────────────────────────────────────────────

    def _time_to_x(self, t: float) -> int:
        return round(t * self._px_per_sec)

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

        if self._beat_mode:
            self._paint_beat_ruler(p, fm)
            return

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

    def _paint_beat_ruler(self, p: QPainter, fm: QFontMetrics) -> None:
        """Draw a beat/bar ruler when beat mode is active."""
        bpm = self._bpm
        offset = self._beat_offset_s
        beats_per_bar = self._time_sig_num
        beat_s = 60.0 / bpm
        bar_s = beats_per_bar * beat_s
        subdiv = self._snap_subdivision

        beat_px = beat_s * self._px_per_sec
        subdiv_px = subdiv * beat_s * self._px_per_sec

        draw_beats = beat_px >= 12
        draw_subdivs = subdiv < 1.0 and subdiv_px >= 6

        # Start at the first bar before t=0
        first_bar = int(_seconds_to_beats(0.0, bpm, offset) / beats_per_bar)
        end_bar = int(_seconds_to_beats(self._duration_s + bar_s, bpm, offset) / beats_per_bar) + 1

        for bar_num in range(first_bar, end_bar + 1):
            bar_beat = bar_num * beats_per_bar  # absolute beat index of bar start
            bar_t = _beats_to_seconds(bar_beat, bpm, offset)
            if bar_t > self._duration_s + bar_s:
                break

            # Bar line (major)
            bx = self._time_to_x(bar_t)
            p.setPen(QPen(QColor("#888888"), 1))
            p.drawLine(bx, RULER_H - 14, bx, RULER_H)
            label = str(bar_num + 1)
            lw = fm.horizontalAdvance(label)
            p.setPen(QColor("#cccccc"))
            p.drawText(bx - lw // 2, RULER_H - 15, label)

            if draw_beats:
                for b in range(1, beats_per_bar):
                    beat_t = _beats_to_seconds(bar_beat + b, bpm, offset)
                    bx2 = self._time_to_x(beat_t)
                    p.setPen(QPen(QColor("#666666"), 1))
                    p.drawLine(bx2, RULER_H - 8, bx2, RULER_H)
                    if beat_px >= 30:
                        bl = str(b + 1)
                        blw = fm.horizontalAdvance(bl)
                        p.setPen(QColor("#999999"))
                        p.drawText(bx2 - blw // 2, RULER_H - 9, bl)

            if draw_subdivs:
                total_subdivs = int(beats_per_bar / subdiv)
                for s in range(1, total_subdivs):
                    if s % int(1.0 / subdiv) == 0:
                        continue  # skip beat boundaries already drawn
                    subdiv_t = _beats_to_seconds(bar_beat + s * subdiv, bpm, offset)
                    sx = self._time_to_x(subdiv_t)
                    p.setPen(QPen(QColor("#444444"), 1))
                    p.drawLine(sx, RULER_H - 4, sx, RULER_H)

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

        # Intro end marker (gold dashed line + diamond handle)
        if self._intro_end_t is not None:
            ix = self._time_to_x(self._intro_end_t)
            gold = QColor("#f0c040")
            pen = QPen(gold, 2)
            pen.setStyle(Qt.PenStyle.DashLine)
            p.setPen(pen)
            p.drawLine(ix, RULER_H, ix, CANVAS_H)
            mid_y = RULER_H + TRACK_H // 2
            d = 7
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(gold)
            p.drawPolygon(QPolygon([
                QPoint(ix,     mid_y - d),
                QPoint(ix + d, mid_y),
                QPoint(ix,     mid_y + d),
                QPoint(ix - d, mid_y),
            ]))
            p.setPen(gold)
            p.drawText(ix + 5, RULER_H + fm.ascent() + 6, "▶ lyrics")

        # Outro start marker (blue dashed line + inverted diamond handle)
        if self._outro_start_t is not None:
            ox = self._time_to_x(self._outro_start_t)
            blue = QColor("#60c0f0")
            pen = QPen(blue, 2)
            pen.setStyle(Qt.PenStyle.DashLine)
            p.setPen(pen)
            p.drawLine(ox, RULER_H, ox, CANVAS_H)
            mid_y = RULER_H + TRACK_H // 2
            d = 7
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(blue)
            p.drawPolygon(QPolygon([
                QPoint(ox,     mid_y + d),
                QPoint(ox + d, mid_y),
                QPoint(ox,     mid_y - d),
                QPoint(ox - d, mid_y),
            ]))
            p.setPen(blue)
            p.drawText(ox + 5, RULER_H + fm.ascent() + 6, "end ◀")

    def _paint_cursor(self, p: QPainter) -> None:
        if self._duration_s <= 0:
            return
        x = self._time_to_x(self._cursor_s)
        p.setPen(QPen(QColor("#ff4444"), 1))
        p.drawLine(x, 0, x, CANVAS_H)

        # Time readout floating in the ruler next to the cursor
        t = self._cursor_s
        if self._beat_mode and self._bpm > 0:
            raw_beat = _seconds_to_beats(t, self._bpm, self._beat_offset_s)
            bar = int(raw_beat // self._time_sig_num) + 1
            beat_in_bar = int(raw_beat % self._time_sig_num) + 1
            frac = raw_beat % 1.0
            sub = int(frac / self._snap_subdivision) + 1 if self._snap_subdivision > 0 else 1
            label = f"{bar}.{beat_in_bar}.{sub}"
        else:
            total_s = int(t)
            tenths = int((t - total_s) * 10)
            label = f"{total_s // 60}:{total_s % 60:02d}.{tenths}"
        font = QFont()
        font.setPointSize(8)
        font.setBold(True)
        p.setFont(font)
        fm = QFontMetrics(font)
        lw = fm.horizontalAdvance(label)
        pad = 3
        # Flip to left of cursor when too close to the right edge
        lx = x + pad if x + pad + lw < self.width() else x - pad - lw
        p.setPen(QColor("#ff4444"))
        p.drawText(lx, RULER_H - 4, label)

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
        # Check outro marker, then intro marker, before lyric markers
        if self._outro_start_t is not None:
            if abs(x - self._time_to_x(self._outro_start_t)) <= HIT_RADIUS:
                self._dragging_outro = True
                return
        if self._intro_end_t is not None:
            if abs(x - self._time_to_x(self._intro_end_t)) <= HIT_RADIUS:
                self._dragging_intro = True
                return
        hit = self._find_marker_at(x)
        if hit >= 0:
            self._dragging = hit
            self._drag_start_time = self._markers[hit].start_time
            self._drag_offset_px = x - self._time_to_x(self._markers[hit].start_time)
            self.marker_selected.emit(hit)
        else:
            t = max(0.0, min(self._duration_s, self._x_to_time(x)))
            self.seek_requested.emit(t)
            self.marker_selected.emit(-1)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._dragging_outro:
            x = event.position().x()
            new_t = max(0.0, min(self._duration_s, self._x_to_time(x)))
            if self._snap:
                new_t = self._snap_time(new_t)
            self._outro_start_t = new_t
            self.outro_marker_moved.emit(new_t)
            self.update()
            return
        if self._dragging_intro:
            x = event.position().x()
            new_t = max(0.0, min(self._duration_s, self._x_to_time(x)))
            if self._snap:
                new_t = self._snap_time(new_t)
            self._intro_end_t = new_t
            self.intro_marker_moved.emit(new_t)
            self.update()
            return
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
            new_t = self._snap_time(new_t)

        self._markers[i].start_time = new_t
        self.marker_moved.emit(i, new_t)
        self.update()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if self._dragging_outro:
            self._dragging_outro = False
            return
        if self._dragging_intro:
            self._dragging_intro = False
            return
        if self._dragging >= 0:
            new_t = self._markers[self._dragging].start_time
            if abs(new_t - self._drag_start_time) > 1e-9:
                self.marker_drag_committed.emit(
                    self._dragging, self._drag_start_time, new_t
                )
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

        self._beat_lbl = QLabel("")
        self._beat_lbl.setStyleSheet("color: #888888; font-style: italic;")
        self._beat_lbl.setFixedWidth(110)
        row.addWidget(self._beat_lbl)

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

    def refresh_beat_label(
        self, beat_mode: bool, bpm: float, time_sig: int, offset: float
    ) -> None:
        if not beat_mode or self._index < 0 or bpm <= 0:
            self._beat_lbl.setText("")
            return
        t = self._start_spin.value()
        raw_beat = _seconds_to_beats(t, bpm, offset)
        bar = int(raw_beat // time_sig) + 1
        beat_in_bar = (raw_beat % time_sig) + 1
        self._beat_lbl.setText(f"Bar {bar}, Beat {beat_in_bar:.2f}")

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
# Undo commands
# ──────────────────────────────────────────────────────────────────────────────

class _MoveMarkerCommand(QUndoCommand):
    def __init__(
        self,
        index: int,
        old_t: float,
        new_t: float,
        markers: list,
        canvas: _TimelineCanvas,
        detail: _MarkerDetailArea,
        duration_s: float,
    ) -> None:
        super().__init__(f"Move marker {index}")
        self._index = index
        self._old_t = old_t
        self._new_t = new_t
        self._markers = markers
        self._canvas = canvas
        self._detail = detail
        self._duration_s = duration_s

    def _apply(self, t: float) -> None:
        self._markers[self._index].start_time = t
        self._canvas.load(self._markers, self._duration_s)
        self._canvas.set_selected(self._index)
        if self._detail._index == self._index:
            self._detail.load(self._index, self._markers, self._duration_s)

    def redo(self) -> None:
        self._apply(self._new_t)

    def undo(self) -> None:
        self._apply(self._old_t)


class _EditTextCommand(QUndoCommand):
    _BASE_ID = 1000  # combined with index to give per-marker merge id

    def __init__(
        self,
        index: int,
        old_text: str,
        new_text: str,
        markers: list,
        canvas: _TimelineCanvas,
        detail: _MarkerDetailArea,
        duration_s: float,
    ) -> None:
        super().__init__(f"Edit text {index}")
        self._index = index
        self._old_text = old_text
        self._new_text = new_text
        self._markers = markers
        self._canvas = canvas
        self._detail = detail
        self._duration_s = duration_s

    def id(self) -> int:  # noqa: A003
        return self._BASE_ID + self._index

    def mergeWith(self, other: QUndoCommand) -> bool:  # noqa: N802
        if other.id() != self.id():
            return False
        self._new_text = other._new_text  # type: ignore[attr-defined]
        return True

    def _apply(self, text: str) -> None:
        self._markers[self._index].text = text
        self._canvas.update()
        if self._detail._index == self._index:
            self._detail.load(self._index, self._markers, self._duration_s)

    def redo(self) -> None:
        self._apply(self._new_text)

    def undo(self) -> None:
        self._apply(self._old_text)


class _InsertMarkerCommand(QUndoCommand):
    def __init__(
        self,
        after_index: int,
        new_marker: "_Marker",
        markers: list,
        canvas: _TimelineCanvas,
        detail: "_MarkerDetailArea",
        duration_s: float,
    ) -> None:
        super().__init__("Insert marker")
        self._after  = after_index
        self._marker = new_marker
        self._markers  = markers
        self._canvas   = canvas
        self._detail   = detail
        self._duration_s = duration_s

    def redo(self) -> None:
        self._markers.insert(self._after + 1, self._marker)
        self._canvas.load(self._markers, self._duration_s)
        self._canvas.set_selected(self._after + 1)
        self._detail.load(self._after + 1, self._markers, self._duration_s)

    def undo(self) -> None:
        self._markers.pop(self._after + 1)
        self._canvas.load(self._markers, self._duration_s)
        self._canvas.set_selected(self._after)
        self._detail.load(self._after, self._markers, self._duration_s)


class _DeleteMarkerCommand(QUndoCommand):
    def __init__(
        self,
        index: int,
        markers: list,
        canvas: _TimelineCanvas,
        detail: "_MarkerDetailArea",
        duration_s: float,
    ) -> None:
        super().__init__("Delete marker")
        self._index  = index
        self._saved  = _Marker(start_time=markers[index].start_time, text=markers[index].text)
        self._markers  = markers
        self._canvas   = canvas
        self._detail   = detail
        self._duration_s = duration_s

    def redo(self) -> None:
        self._markers.pop(self._index)
        self._canvas.load(self._markers, self._duration_s)
        new_sel = min(self._index, len(self._markers) - 1)
        self._canvas.set_selected(new_sel)
        self._detail.load(new_sel, self._markers, self._duration_s)

    def undo(self) -> None:
        self._markers.insert(self._index, self._saved)
        self._canvas.load(self._markers, self._duration_s)
        self._canvas.set_selected(self._index)
        self._detail.load(self._index, self._markers, self._duration_s)


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
        self._title:       str = ""
        self._artist:      str = ""
        self._intro_end_t:  float | None = None
        self._outro_start_t: float | None = None
        self._gap_after_indices: set[int] = set()
        self._zoom         = 1.0           # multiplier on BASE_PX_PER_SEC
        self._stamp_cursor = 0             # next marker index to stamp via Enter

        self._undo_stack = QUndoStack(self)
        self._undo_stack.cleanChanged.connect(self._on_clean_changed)

        self._follow_playhead = True
        self._scroll_timer = QTimer(self)
        self._scroll_timer.setInterval(16)
        self._scroll_timer.timeout.connect(self._smooth_scroll_tick)

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
        self._title  = data.get("title") or ""
        self._artist = data.get("artist") or ""
        self._intro_end_t = data.get("intro_end_time")
        self._outro_start_t = data.get("outro_start_time")
        _bpm        = data.get("bpm") or 120.0
        _time_sig   = data.get("time_sig_num") or 4
        _beat_off   = data.get("beat_offset_s") or 0.0

        # Record which lyric-line indices are followed by a mid-array gap entry,
        # so they survive the round-trip through save_lyrics().
        self._gap_after_indices = set()
        try:
            raw_json = json.loads(Path(lyrics_path).read_text(encoding="utf-8"))
            lyric_idx = -1
            for entry in raw_json.get("lyrics", []):
                if entry.get("text") == "":
                    if lyric_idx >= 0:
                        self._gap_after_indices.add(lyric_idx)
                else:
                    lyric_idx += 1
            # The final empty entry is the end marker; remove it from the set
            # (it's always re-appended explicitly by _write_lyrics).
            self._gap_after_indices.discard(lyric_idx)
        except Exception:
            pass  # Non-fatal; gaps simply won't be preserved

        self._dirty = False
        self._stamp_cursor = 0
        self._undo_stack.clear()

        self._title_edit.setText(self._title)
        self._canvas.load(self._markers, self._duration_s)
        self._canvas.set_intro_marker(self._intro_end_t)
        self._clear_intro_btn.setEnabled(self._intro_end_t is not None)
        self._canvas.set_outro_marker(self._outro_start_t)
        self._clear_outro_btn.setEnabled(self._outro_start_t is not None)
        self._detail.load(-1, self._markers, self._duration_s)
        self._detail.set_dirty(False)
        self.setTitle(f"Timeline Editor — {self._title}")

        # Restore beat settings without triggering dirty
        _beat_widgets = (
            self._bpm_spin, self._time_sig_spin,
            self._beat_offset_spin, self._subdiv_combo, self._beat_mode_cb,
        )
        for _w in _beat_widgets:
            _w.blockSignals(True)
        self._bpm_spin.setValue(_bpm)
        self._time_sig_spin.setValue(_time_sig)
        self._beat_offset_spin.setValue(_beat_off)
        self._beat_mode_cb.setChecked(False)  # always off on song load
        for _w in _beat_widgets:
            _w.blockSignals(False)
        # Push params to canvas/detail (no dirty side-effect)
        self._canvas.set_beat_params(
            False, _bpm, _time_sig, _beat_off,
            self._subdiv_combo.currentData(),
        )
        self._detail.refresh_beat_label(False, _bpm, _time_sig, _beat_off)

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Canvas (must exist before toolbar connects snap checkbox)
        self._canvas = _TimelineCanvas()
        self._canvas.marker_moved.connect(self._on_marker_moved)
        self._canvas.marker_drag_committed.connect(self._on_marker_drag_committed)
        self._canvas.marker_selected.connect(self._on_marker_selected)
        self._canvas.seek_requested.connect(self._on_seek_requested)
        self._canvas.intro_marker_moved.connect(self._on_intro_marker_moved)
        self._canvas.outro_marker_moved.connect(self._on_outro_marker_moved)

        layout.addLayout(self._build_toolbar())

        # Song Info row (title + artist editable fields)
        info_row = QHBoxLayout()
        info_row.setSpacing(6)
        info_row.addWidget(QLabel("Title:"))
        self._title_edit = QLineEdit()
        self._title_edit.setPlaceholderText("Song title")
        self._title_edit.textEdited.connect(self._on_title_edited)
        info_row.addWidget(self._title_edit, stretch=2)
        layout.addLayout(info_row)

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

        self._beat_mode_cb = QCheckBox("Beat Mode")
        self._beat_mode_cb.setToolTip("Switch ruler and snap to beat/bar grid")
        self._beat_mode_cb.toggled.connect(self._on_beat_mode_toggled)
        row.addWidget(self._beat_mode_cb)

        self._bpm_spin = QDoubleSpinBox()
        self._bpm_spin.setRange(20.0, 300.0)
        self._bpm_spin.setValue(120.0)
        self._bpm_spin.setDecimals(1)
        self._bpm_spin.setSuffix(" BPM")
        self._bpm_spin.setFixedWidth(90)
        self._bpm_spin.setEnabled(False)
        self._bpm_spin.setToolTip("Beats per minute")
        self._bpm_spin.valueChanged.connect(self._on_beat_params_changed)
        row.addWidget(self._bpm_spin)

        self._time_sig_spin = QSpinBox()
        self._time_sig_spin.setRange(1, 16)
        self._time_sig_spin.setValue(4)
        self._time_sig_spin.setSuffix("/4")
        self._time_sig_spin.setFixedWidth(52)
        self._time_sig_spin.setEnabled(False)
        self._time_sig_spin.setToolTip("Beats per bar (time signature numerator)")
        self._time_sig_spin.valueChanged.connect(self._on_beat_params_changed)
        row.addWidget(self._time_sig_spin)

        self._beat_offset_spin = QDoubleSpinBox()
        self._beat_offset_spin.setRange(-10.0, 60.0)
        self._beat_offset_spin.setValue(0.0)
        self._beat_offset_spin.setDecimals(3)
        self._beat_offset_spin.setSuffix("s off")
        self._beat_offset_spin.setFixedWidth(90)
        self._beat_offset_spin.setEnabled(False)
        self._beat_offset_spin.setToolTip("Beat 1 offset in seconds (for pickup bars or intro silence)")
        self._beat_offset_spin.valueChanged.connect(self._on_beat_params_changed)
        row.addWidget(self._beat_offset_spin)

        self._subdiv_combo = QComboBox()
        for lbl, val in [("1 beat", 1.0), ("1/2 beat", 0.5), ("1/4 beat", 0.25), ("1/8 beat", 0.125)]:
            self._subdiv_combo.addItem(lbl, val)
        self._subdiv_combo.setCurrentIndex(2)  # default: 1/4 beat
        self._subdiv_combo.setEnabled(False)
        self._subdiv_combo.setToolTip("Snap resolution within a beat")
        self._subdiv_combo.currentIndexChanged.connect(self._on_beat_params_changed)
        row.addWidget(self._subdiv_combo)

        self._follow_cb = QCheckBox("Follow playhead")
        self._follow_cb.setChecked(True)
        self._follow_cb.setToolTip("Auto-scroll to keep the playhead in view during playback")
        self._follow_cb.toggled.connect(lambda checked: setattr(self, '_follow_playhead', checked))
        row.addWidget(self._follow_cb)

        row.addStretch()

        self._insert_btn = QPushButton("+ Insert")
        self._insert_btn.setFixedWidth(72)
        self._insert_btn.setToolTip("Insert a new blank marker after the selected one")
        self._insert_btn.setEnabled(False)
        self._insert_btn.clicked.connect(self._on_insert)
        row.addWidget(self._insert_btn)

        self._delete_btn = QPushButton("− Delete")
        self._delete_btn.setFixedWidth(72)
        self._delete_btn.setToolTip("Delete the selected marker")
        self._delete_btn.setEnabled(False)
        self._delete_btn.clicked.connect(self._on_delete)
        row.addWidget(self._delete_btn)

        self._set_intro_btn = QPushButton("Set Intro ▶")
        self._set_intro_btn.setFixedWidth(90)
        self._set_intro_btn.setToolTip("Place intro end marker at current playback position")
        self._set_intro_btn.clicked.connect(self._on_set_intro)
        row.addWidget(self._set_intro_btn)

        self._clear_intro_btn = QPushButton("Clear Intro")
        self._clear_intro_btn.setFixedWidth(85)
        self._clear_intro_btn.setToolTip("Remove the intro end marker (disables title card)")
        self._clear_intro_btn.setEnabled(False)
        self._clear_intro_btn.clicked.connect(self._on_clear_intro)
        row.addWidget(self._clear_intro_btn)

        self._set_outro_btn = QPushButton("Set Outro ◀")
        self._set_outro_btn.setFixedWidth(90)
        self._set_outro_btn.setToolTip("Place outro start marker at current playback position")
        self._set_outro_btn.clicked.connect(self._on_set_outro)
        row.addWidget(self._set_outro_btn)

        self._clear_outro_btn = QPushButton("Clear Outro")
        self._clear_outro_btn.setFixedWidth(85)
        self._clear_outro_btn.setToolTip("Remove the outro start marker")
        self._clear_outro_btn.setEnabled(False)
        self._clear_outro_btn.clicked.connect(self._on_clear_outro)
        row.addWidget(self._clear_outro_btn)

        return row

    # ── AudioPlayer connection ────────────────────────────────────────────────

    def _connect_player(self) -> None:
        self._player.position_changed.connect(self._on_position_changed)
        self._player.duration_changed.connect(self._on_duration_changed)
        self._player.playback_state_changed.connect(self._on_playback_state_changed)

    def _on_position_changed(self, ms: int) -> None:
        # During playback the timer drives cursor + scroll together in one frame.
        # Only update cursor here when paused (e.g. user is seeking).
        if not self._player.is_playing:
            self._canvas.set_cursor(ms / 1000.0)

    def _on_duration_changed(self, ms: int) -> None:
        self._duration_s = ms / 1000.0
        self._canvas.load(self._markers, self._duration_s)

    # ── follow-playhead scroll ────────────────────────────────────────────────

    def _on_playback_state_changed(self, state) -> None:
        from PyQt6.QtMultimedia import QMediaPlayer
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self._scroll_timer.start()
        else:
            self._scroll_timer.stop()

    def _smooth_scroll_tick(self) -> None:
        """Single update point during playback: move cursor and scroll together."""
        t        = self._player.position / 1000.0
        cursor_x = int(t * self._px_per_sec())
        self._canvas.set_cursor(t)
        if self._follow_playhead:
            sb   = self._scroll.horizontalScrollBar()
            vp_w = self._scroll.viewport().width()
            sb.setValue(max(0, cursor_x - int(vp_w * 0.30)))

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
        # Live update during drag — no undo push yet (committed on mouseRelease)
        self._detail.load(index, self._markers, self._duration_s)

    def _on_marker_drag_committed(self, index: int, old_t: float, new_t: float) -> None:
        cmd = _MoveMarkerCommand(
            index, old_t, new_t, self._markers, self._canvas, self._detail, self._duration_s
        )
        self._undo_stack.push(cmd)

    def _on_marker_selected(self, index: int) -> None:
        self._canvas.set_selected(index)
        self._detail.load(index, self._markers, self._duration_s)
        if index >= 0:
            self._stamp_cursor = index
        has_sel = index >= 0
        self._insert_btn.setEnabled(has_sel)
        self._delete_btn.setEnabled(has_sel)

    def _on_seek_requested(self, time_s: float) -> None:
        self._player.seek(int(time_s * 1000))

    # ── detail area signals ───────────────────────────────────────────────────

    def _on_text_changed(self, index: int, text: str) -> None:
        if 0 <= index < len(self._markers):
            old_text = self._markers[index].text
            cmd = _EditTextCommand(
                index, old_text, text, self._markers, self._canvas, self._detail, self._duration_s
            )
            self._undo_stack.push(cmd)

    def _on_time_changed(self, index: int, new_t: float) -> None:
        if 0 <= index < len(self._markers):
            i = index
            old_t = self._markers[i].start_time
            min_t = self._markers[i - 1].start_time + MIN_GAP_S if i > 0 else 0.0
            max_t = (
                self._markers[i + 1].start_time - MIN_GAP_S
                if i + 1 < len(self._markers)
                else self._duration_s
            )
            new_t = max(min_t, min(max_t, new_t))
            if abs(new_t - old_t) > 1e-9:
                cmd = _MoveMarkerCommand(
                    i, old_t, new_t, self._markers, self._canvas, self._detail, self._duration_s
                )
                self._undo_stack.push(cmd)

    def _on_prev(self) -> None:
        idx = self._canvas._selected
        if idx > 0:
            self._on_marker_selected(idx - 1)

    def _on_next(self) -> None:
        idx = self._canvas._selected
        if 0 <= idx < len(self._markers) - 1:
            self._on_marker_selected(idx + 1)

    def _on_insert(self) -> None:
        idx = self._canvas._selected
        if idx < 0 or not self._markers:
            return
        end_t = (
            self._markers[idx + 1].start_time
            if idx + 1 < len(self._markers)
            else self._duration_s
        )
        new_t = (self._markers[idx].start_time + end_t) / 2.0
        new_marker = _Marker(start_time=new_t, text="")
        cmd = _InsertMarkerCommand(
            idx, new_marker, self._markers, self._canvas, self._detail, self._duration_s
        )
        self._undo_stack.push(cmd)
        self._stamp_cursor = idx + 1

    def _on_delete(self) -> None:
        idx = self._canvas._selected
        if idx < 0 or not self._markers:
            return
        cmd = _DeleteMarkerCommand(
            idx, self._markers, self._canvas, self._detail, self._duration_s
        )
        self._undo_stack.push(cmd)
        if self._stamp_cursor > idx:
            self._stamp_cursor = max(0, self._stamp_cursor - 1)

    # ── intro marker + song info handlers ────────────────────────────────────

    def _on_title_edited(self, text: str) -> None:
        self._title = text
        self._set_extras_dirty()


    def _on_set_intro(self) -> None:
        t = self._canvas._cursor_s
        self._intro_end_t = t
        self._canvas.set_intro_marker(t)
        self._clear_intro_btn.setEnabled(True)
        self._set_extras_dirty()

    def _on_clear_intro(self) -> None:
        self._intro_end_t = None
        self._canvas.set_intro_marker(None)
        self._clear_intro_btn.setEnabled(False)
        self._set_extras_dirty()

    def _on_intro_marker_moved(self, t: float) -> None:
        self._intro_end_t = t
        self._set_extras_dirty()

    def _on_set_outro(self) -> None:
        t = self._canvas._cursor_s
        self._outro_start_t = t
        self._canvas.set_outro_marker(t)
        self._clear_outro_btn.setEnabled(True)
        self._set_extras_dirty()

    def _on_clear_outro(self) -> None:
        self._outro_start_t = None
        self._canvas.set_outro_marker(None)
        self._clear_outro_btn.setEnabled(False)
        self._set_extras_dirty()

    def _on_outro_marker_moved(self, t: float) -> None:
        self._outro_start_t = t
        self._set_extras_dirty()

    # ── beat mode handlers ────────────────────────────────────────────────────

    def _on_beat_mode_toggled(self, enabled: bool) -> None:
        for w in (self._bpm_spin, self._time_sig_spin, self._beat_offset_spin, self._subdiv_combo):
            w.setEnabled(enabled)
        if enabled:
            self._snap_cb.setText(f"Snap {self._subdiv_combo.currentText()}")
        else:
            self._snap_cb.setText("Snap 0.1s")
        self._on_beat_params_changed()

    def _on_beat_params_changed(self) -> None:
        enabled = self._beat_mode_cb.isChecked()
        if enabled:
            self._snap_cb.setText(f"Snap {self._subdiv_combo.currentText()}")
        self._canvas.set_beat_params(
            enabled,
            self._bpm_spin.value(),
            self._time_sig_spin.value(),
            self._beat_offset_spin.value(),
            self._subdiv_combo.currentData(),
        )
        self._detail.refresh_beat_label(
            enabled,
            self._bpm_spin.value(),
            self._time_sig_spin.value(),
            self._beat_offset_spin.value(),
        )
        self._set_extras_dirty()

    def _set_extras_dirty(self) -> None:
        """Mark dirty for changes that bypass the undo stack (title/artist/intro)."""
        self._dirty = True
        self._detail.set_dirty(True)
        self.lyrics_modified.emit()

    # ── save ──────────────────────────────────────────────────────────────────

    def _on_save(self) -> None:
        if not self._lyrics_path:
            return
        try:
            self._write_lyrics(self._lyrics_path)
        except Exception as exc:
            QMessageBox.critical(self, "Save Error", str(exc))
            return
        self._undo_stack.setClean()   # triggers _on_clean_changed(True)
        # Also clear dirty explicitly — title/artist/intro bypass the undo stack,
        # so if the stack was already clean, cleanChanged won't fire again.
        self._dirty = False
        self._detail.set_dirty(False)

    def _write_lyrics(self, path: str) -> None:
        filepath = Path(path)
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        data["title"] = self._title
        if self._intro_end_t is not None:
            data["intro_end_time"] = round(self._intro_end_t, 3)
        else:
            data.pop("intro_end_time", None)
        if self._outro_start_t is not None:
            data["outro_start_time"] = round(self._outro_start_t, 3)
        else:
            data.pop("outro_start_time", None)
        data["bpm"] = round(self._bpm_spin.value(), 1)
        data["time_sig_num"] = self._time_sig_spin.value()
        data["beat_offset_s"] = round(self._beat_offset_spin.value(), 3)

        raw_lyrics = []
        for i, m in enumerate(self._markers):
            raw_lyrics.append({"time": round(m.start_time, 3), "text": m.text})
            if i in self._gap_after_indices:
                raw_lyrics.append({"time": round(m.start_time, 3), "text": ""})
        # End marker: use audio duration when known, else preserved original
        end_t = self._duration_s if self._duration_s > 0 else self._end_marker_t
        raw_lyrics.append({"time": round(end_t, 3), "text": ""})
        data["lyrics"] = raw_lyrics

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    # ── dirty / undo ──────────────────────────────────────────────────────────

    def _on_clean_changed(self, clean: bool) -> None:
        self._dirty = not clean
        self._detail.set_dirty(self._dirty)
        if self._dirty:
            self.lyrics_modified.emit()

    # ── public API for MainWindow ─────────────────────────────────────────────

    @property
    def step_size_ms(self) -> int:
        """Current snap step in ms — 100ms in time mode, beat subdivision in beat mode."""
        if self._beat_mode_cb.isChecked():
            subdiv = self._subdiv_combo.currentData()
            bpm = self._bpm_spin.value()
            if bpm > 0 and subdiv and subdiv > 0:
                return max(1, int(60_000 / bpm * subdiv))
        return 100

    def undo(self) -> None:
        self._undo_stack.undo()
        # Undo calls canvas.set_selected() directly, bypassing _on_marker_selected.
        # Sync _stamp_cursor so the next Enter re-stamps the undone marker.
        idx = self._canvas._selected
        if idx >= 0:
            self._stamp_cursor = idx

    def redo(self) -> None:
        self._undo_stack.redo()
        # After redo the redone marker is selected; advance cursor past it.
        idx = self._canvas._selected
        if idx >= 0:
            self._stamp_cursor = idx + 1

    def save_lyrics(self) -> None:
        self._on_save()

    def stamp_current(self) -> None:
        """Stamp the selected marker to the current playback position, then advance selection.

        If a marker is explicitly selected, stamp that one and sync the stamp
        cursor to it.  If nothing is selected, resume from the stamp cursor so
        that seeking (which clears the selection) never accidentally resets
        stamping back to marker 0.
        """
        if not self._markers:
            return

        idx = self._canvas._selected
        if idx < 0:
            # Nothing selected — resume from where we left off, not from 0.
            idx = self._stamp_cursor
            if idx >= len(self._markers):
                return
            self._on_marker_selected(idx)

        new_t = self._canvas._cursor_s
        old_t = self._markers[idx].start_time

        # Only clamp against the previous marker — the next marker hasn't been
        # stamped yet, so its current position must not constrain this stamp.
        min_t = self._markers[idx - 1].start_time + MIN_GAP_S if idx > 0 else 0.0
        new_t = max(min_t, new_t)

        if abs(new_t - old_t) > 1e-9:
            cmd = _MoveMarkerCommand(
                idx, old_t, new_t, self._markers, self._canvas, self._detail, self._duration_s
            )
            self._undo_stack.push(cmd)

        next_idx = idx + 1
        self._stamp_cursor = next_idx
        if next_idx < len(self._markers):
            self._on_marker_selected(next_idx)
