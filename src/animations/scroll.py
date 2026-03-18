"""Continuous scrolling lyric animation engine."""

import math
from dataclasses import dataclass

import numpy as np

WIDTH = 1920
HEIGHT = 1080

# Maximum seconds before the next line's start_time to begin scrolling.
SCROLL_LEAD_SECONDS = 1.5

# Fraction of the time between consecutive start_times to use for scrolling.
# The remainder is a stationary hold while the current line is highlighted.
# e.g. 0.40 → scroll occupies at most 40% of a line's slot.
SCROLL_LEAD_FRACTION = 0.40

# How many seconds before the first lyric line to begin the pre-roll scroll.
INTRO_SCROLL_SECONDS = 3.0


@dataclass
class LineRenderInfo:
    text: str
    screen_y: float   # center y position on screen in pixels
    alpha: float      # 0.0 – 1.0
    is_active: bool
    is_title: bool = False  # True for the title text line in intro/outro cards


class ScrollingAnimation:
    """Renders all lyric lines as a continuous scrolling stream.

    Virtual space: line i sits at y = i * line_height.  Each line holds
    at the center for most of its slot, then the view glides to the next
    line's center position, arriving exactly at that line's start_time.

    If intro_lines and intro_end_time are supplied, the animation starts with
    a static title card (last intro line centered, others above) that scrolls
    smoothly upward into the lyric queue at intro_end_time.

    If outro_lines and outro_start_time are supplied, the animation ends with
    a smooth scroll into a static title card (mirroring the intro) that holds
    for the remainder of the video.
    """

    def __init__(self, lines, fps: int, line_height: int = 120,
                 inactive_alphas: list | None = None,
                 intro_lines: list[str] | None = None,
                 intro_end_time: float | None = None,
                 outro_lines: list[str] | None = None,
                 outro_start_time: float | None = None):
        self.lines = lines
        self.fps = fps
        self.line_height = line_height
        # Length controls how many lines are visible each side of center.
        self.inactive_alphas = inactive_alphas or [0.6, 0.4, 0.2]
        self._max_visible_dist = len(self.inactive_alphas) + 1
        # Title card intro support
        self._intro_lines: list[str] = intro_lines or []
        self._intro_end_time: float | None = intro_end_time
        # Title card outro support
        self._outro_lines: list[str] = outro_lines or []
        self._outro_start_time: float | None = outro_start_time
        self._transitions = self._compute_transitions()

    # ------------------------------------------------------------------
    # Pre-computation
    # ------------------------------------------------------------------

    def _compute_transitions(self) -> list[tuple[float, float, int, int]]:
        """Build (t_start, t_end, from_idx, to_idx) for each line change.

        Transitions are anchored to consecutive start_times, not end_times.
        Because the lyrics parser sets end_time[i] = start_time[i+1], there
        is never a true gap between lines.  Instead, each line occupies a
        time slot from start_time[i] to start_time[i+1]; the scroll uses the
        trailing SCROLL_LEAD_FRACTION of that slot so the view arrives at the
        next line's center exactly at start_time[i+1].
        """
        result = []
        for i in range(len(self.lines) - 1):
            t_next = self.lines[i + 1].start_time
            t_this = self.lines[i].start_time
            available = t_next - t_this  # full slot for line i

            # Scroll duration: smaller of the cap or a fraction of the slot.
            scroll_dur = min(SCROLL_LEAD_SECONDS, available * SCROLL_LEAD_FRACTION)

            t_end = t_next            # scroll completes exactly when next line starts
            t_start = t_end - scroll_dur

            result.append((t_start, t_end, i, i + 1))
        return result

    # ------------------------------------------------------------------
    # Per-frame queries
    # ------------------------------------------------------------------

    def _find_active_idx(self, t: float) -> int:
        """Return index of the currently sung line, or last sung line."""
        last_idx = -1
        for i, line in enumerate(self.lines):
            if line.start_time <= t:
                last_idx = i
            if line.start_time <= t < line.end_time:
                return i
        return last_idx

    def _compute_lyric_scroll_pos(self, t: float) -> float:
        """Normal lyric transition/hold logic (no intro/outro)."""
        for t_start, t_end, from_idx, to_idx in self._transitions:
            if t_start <= t <= t_end:
                if t_end == t_start:
                    return to_idx * self.line_height
                raw = (t - t_start) / (t_end - t_start)
                eased = raw * raw * (3.0 - 2.0 * raw)
                return from_idx * self.line_height + eased * self.line_height

        # No active transition — rest at the most recently reached position.
        for t_start, t_end, from_idx, to_idx in reversed(self._transitions):
            if t >= t_end:
                return to_idx * self.line_height

        # Before any transition has started (early in the song).
        active_idx = self._find_active_idx(t)
        if active_idx < 0:
            return 0.0
        return active_idx * self.line_height

    def _compute_scroll_pos(self, t: float) -> float:
        """Virtual y coordinate that should be centered on screen at time t."""
        if self._intro_lines and self._intro_end_time is not None:
            # Title card phase: camera rests at a position that centers the
            # last intro line (title).  Virtual position = -max_visible_dist * lh
            # so that lyric lines are just beyond the alpha fade boundary.
            static_pos = -self._max_visible_dist * self.line_height
            intro_start_t = max(0.0, self._intro_end_time - INTRO_SCROLL_SECONDS)
            if t <= intro_start_t:
                return static_pos
            if t < self._intro_end_time:
                raw = (t - intro_start_t) / INTRO_SCROLL_SECONDS
                eased = raw * raw * (3.0 - 2.0 * raw)
                return static_pos * (1.0 - eased)   # static_pos → 0
            # t >= intro_end_time: fall through to outro/lyric logic

        elif self.lines and t < self.lines[0].start_time:
            # Standard pre-roll (no title card): scroll lines 0 and 1 up from below.
            first_start = self.lines[0].start_time
            intro_start_t = max(0.0, first_start - INTRO_SCROLL_SECONDS)
            intro_start_pos = -2.0 * self.line_height  # lines 0+1 below center
            if t <= intro_start_t:
                return intro_start_pos
            raw = (t - intro_start_t) / (first_start - intro_start_t)
            eased = raw * raw * (3.0 - 2.0 * raw)
            return intro_start_pos * (1.0 - eased)  # approaches 0.0 (line 0 at center)

        # Outro phase: transition to static card below the lyric space.
        if self._outro_lines and self._outro_start_time is not None and t >= self._outro_start_time:
            outro_static_pos = (len(self.lines) - 1 + self._max_visible_dist) * self.line_height
            outro_end_t = self._outro_start_time + INTRO_SCROLL_SECONDS
            if t >= outro_end_t:
                return outro_static_pos
            from_pos = self._compute_lyric_scroll_pos(self._outro_start_time)
            raw = (t - self._outro_start_time) / INTRO_SCROLL_SECONDS
            eased = raw * raw * (3.0 - 2.0 * raw)
            return from_pos + eased * (outro_static_pos - from_pos)

        return self._compute_lyric_scroll_pos(t)

    def _screen_pos_to_alpha(self, screen_y: float) -> float:
        """Continuous opacity: 1.0 at center, cosine taper to 0.0 at max visible distance.

        Uses the length of inactive_alphas to determine how many line-slots are
        rendered in each direction (e.g. 3 values → up to 3 lines each side).
        """
        dist_lines = abs(screen_y - HEIGHT / 2.0) / self.line_height
        max_dist = len(self.inactive_alphas) + 1  # e.g. 4.0 with default [0.6,0.4,0.2]
        if dist_lines >= max_dist:
            return 0.0
        return 0.5 * (1.0 + math.cos(math.pi * dist_lines / max_dist))

    def get_visible_lines(self, t: float) -> list[LineRenderInfo]:
        """Return render info for every line visible at time t."""
        scroll_pos = self._compute_scroll_pos(t)
        active_idx = self._find_active_idx(t)
        center_y = HEIGHT / 2.0
        max_dist = self._max_visible_dist

        visible: list[LineRenderInfo] = []

        # Intro lines: shown only before intro_end_time.
        # Virtual positions place them just above the lyric space so they reach
        # exactly alpha=0 by the time the transition completes (scroll_pos → 0).
        if self._intro_lines and self._intro_end_time is not None and t < self._intro_end_time:
            n_intro = len(self._intro_lines)
            is_static = t < max(0.0, self._intro_end_time - INTRO_SCROLL_SECONDS)
            for idx, text in enumerate(self._intro_lines):
                # e.g. for [artist, title] with max_dist=4:
                #   artist → virtual y = -(4+2-1-0)*lh = -5*lh
                #   title  → virtual y = -(4+2-1-1)*lh = -4*lh  (= -max_dist*lh, centered when static)
                virt_y = -(max_dist + n_intro - 1 - idx) * self.line_height
                screen_y = virt_y - scroll_pos + center_y
                dist_lines = abs(screen_y - center_y) / self.line_height
                if dist_lines >= max_dist:
                    continue
                # Title (last intro line) is rendered as "active" during static phase
                is_active = (idx == n_intro - 1) and is_static
                is_title = (idx == n_intro - 1) and text != "__LOGO__"
                visible.append(LineRenderInfo(
                    text=text,
                    screen_y=screen_y,
                    alpha=self._screen_pos_to_alpha(screen_y),
                    is_active=is_active,
                    is_title=is_title,
                ))

            # During the fully static phase lyric lines are beyond max_dist anyway,
            # but return early for clarity and to skip the loop.
            if is_static:
                return visible

        # Outro lines: shown from outro_start_time onward.
        # Virtual positions place them just below the lyric space; the title
        # (last outro line) centers at outro_static_pos.
        if self._outro_lines and self._outro_start_time is not None and t >= self._outro_start_time:
            n_outro = len(self._outro_lines)
            outro_static_pos = (len(self.lines) - 1 + max_dist) * self.line_height
            is_static = t >= self._outro_start_time + INTRO_SCROLL_SECONDS
            for idx, text in enumerate(self._outro_lines):
                # title (last, idx=n_outro-1) at outro_static_pos;
                # artist (idx=0) one slot above (offset = -1 for 2-line outro)
                offset = idx - (n_outro - 1)
                virt_y = outro_static_pos + offset * self.line_height
                screen_y = virt_y - scroll_pos + center_y
                dist_lines = abs(screen_y - center_y) / self.line_height
                if dist_lines >= max_dist:
                    continue
                is_active = (idx == n_outro - 1) and is_static
                is_title = (idx == n_outro - 1) and text != "__LOGO__"
                visible.append(LineRenderInfo(
                    text=text,
                    screen_y=screen_y,
                    alpha=self._screen_pos_to_alpha(screen_y),
                    is_active=is_active,
                    is_title=is_title,
                ))
            if is_static:
                return visible  # lyric lines fully faded — skip their loop

        # Lyric lines
        for i, line in enumerate(self.lines):
            screen_y = (i * self.line_height) - scroll_pos + center_y
            if screen_y < -self.line_height or screen_y > HEIGHT + self.line_height:
                continue

            dist_lines = abs(screen_y - center_y) / self.line_height
            if dist_lines >= max_dist:
                continue

            visible.append(LineRenderInfo(
                text=line.text,
                screen_y=screen_y,
                alpha=self._screen_pos_to_alpha(screen_y),
                is_active=(i == active_idx),
            ))

        return visible

    def make_frame(self, t: float, renderer, background=None) -> np.ndarray:
        """Return a HxWx3 uint8 numpy array for time t."""
        active_idx = self._find_active_idx(t)

        # Compute how far through the active line we are (0.0 – 1.0).
        highlight_progress = 0.0
        if active_idx >= 0:
            active_line = self.lines[active_idx]
            if active_line.duration > 0:
                raw = (t - active_line.start_time) / active_line.duration
                highlight_progress = max(0.0, min(1.0, raw))

        lines_data = [
            {
                "text": li.text,
                "screen_y": li.screen_y,
                "alpha": li.alpha,
                "is_active": li.is_active,
                "is_title": li.is_title,
                "highlight_progress": highlight_progress if li.is_active else 0.0,
            }
            for li in self.get_visible_lines(t)
        ]
        img = renderer.render_scroll_frame(lines_data, background=background)
        return np.array(img.convert("RGB"), dtype=np.uint8)
