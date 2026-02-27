"""Main video generation engine."""

import threading
from pathlib import Path
from typing import Callable


class RenderCancelled(Exception):
    """Raised inside make_frame when the caller requests cancellation."""

import numpy as np
from PIL import Image
from moviepy import VideoClip, VideoFileClip

from src.animations.scroll import ScrollingAnimation
from src.core.audio_handler import load_audio
from src.core.lyrics_parser import parse_lyrics
from src.core.text_renderer import TextRenderer
from src.core.theme_loader import Theme, load_theme

FPS_DEFAULT = 30

# Target output resolution
_WIDTH = 1920
_HEIGHT = 1080


def _fit_to_frame(img: Image.Image) -> Image.Image:
    """Scale and center-crop a PIL image to 1920×1080 (cover mode)."""
    orig_w, orig_h = img.size
    scale = max(_WIDTH / orig_w, _HEIGHT / orig_h)
    new_w = int(orig_w * scale)
    new_h = int(orig_h * scale)
    img = img.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - _WIDTH) // 2
    top = (new_h - _HEIGHT) // 2
    return img.crop((left, top, left + _WIDTH, top + _HEIGHT))


def _build_bg_frame_getter(
    background_path: str | Path,
) -> Callable[[float], Image.Image]:
    """Return a function that maps video time t → background PIL Image.

    Implements ping-pong looping: the clip plays forward then in reverse,
    repeating as many times as needed.  The seam between the end of the
    reverse pass and the start of the next forward pass is seamless because
    both meet at frame 0 of the source clip.
    """
    clip = VideoFileClip(str(background_path))
    bg_dur = clip.duration
    cycle = 2.0 * bg_dur
    # Small epsilon to avoid requesting a frame exactly at the last second
    # (some decoders are off-by-one at the boundary).
    _eps = 1.0 / 60.0

    def get_bg_frame(t: float) -> Image.Image:
        ct = t % cycle
        bg_t = ct if ct <= bg_dur else cycle - ct
        # Clamp within valid range
        bg_t = min(max(bg_t, 0.0), bg_dur - _eps)
        frame = clip.get_frame(bg_t)  # HxWx3 uint8
        img = Image.fromarray(frame.astype(np.uint8), "RGB").convert("RGBA")
        return _fit_to_frame(img)

    return get_bg_frame


def generate_video(
    lyrics_path: str | Path,
    audio_path: str | Path,
    output_path: str | Path,
    theme_path: str | Path | None = None,
    theme: Theme | None = None,
    fps: int = FPS_DEFAULT,
    preview: bool = False,
    preview_start: float = 0.0,
    background_path: str | Path | None = None,
    lyric_position: str | None = None,
    highlight_mode: str | None = None,
    logger: str | None = "bar",
    progress_callback: Callable[[int, int], None] | None = None,
    cancel_event: threading.Event | None = None,
) -> Path:
    """Generate a lyric video from lyrics JSON and an audio file.

    Args:
        lyrics_path: Path to lyrics JSON file.
        audio_path: Path to audio file.
        output_path: Path for the output MP4.
        theme_path: Path to theme JSON (None for default theme).
        fps: Frames per second (default 30).
        preview: If True, only generate the first 30 seconds.
        background_path: Path to background video (None for solid color).

    Returns:
        The output file path.
    """
    # Load inputs
    lyrics_data = parse_lyrics(lyrics_path)
    audio = load_audio(audio_path)
    theme_obj = theme if theme is not None else load_theme(theme_path)
    if lyric_position is not None:
        theme_obj.lyric_position = lyric_position
    if highlight_mode is not None:
        theme_obj.highlight_mode = highlight_mode
    renderer = TextRenderer(theme_obj)

    lines = lyrics_data["lines"]
    intro_end_time = lyrics_data.get("intro_end_time")
    total_duration = audio.duration
    if preview:
        total_duration = max(min(audio.duration - preview_start, 30.0), 0.0)
        # Keep all lines — those beyond total_duration are never reached by
        # make_frame(t) but are needed so the scroll queue shows upcoming lines
        # right up to the end of the preview window.

    print(f"Generating video: {lyrics_data['title']} by {lyrics_data['artist']}")
    print(f"FPS: {fps} | Duration: {total_duration:.1f}s | Lyric lines: {len(lines)}")

    # Build background frame getter (ping-pong loop) if a video was provided
    bg_frame_getter = None
    if background_path is not None:
        print(f"Background: {background_path} (ping-pong loop)")
        bg_frame_getter = _build_bg_frame_getter(background_path)

    # Build scrolling animation over all lines
    animation = ScrollingAnimation(
        lines=lines,
        fps=fps,
        line_height=theme_obj.line_height,
        inactive_alphas=theme_obj.inactive_text_opacity_gradient,
        intro_lines=(
            [
                "__LOGO__" if theme_obj.logo_path else lyrics_data.get("artist", ""),
                lyrics_data["title"],
            ]
            if intro_end_time is not None else None
        ),
        intro_end_time=intro_end_time,
    )

    total_frames = max(int(total_duration * fps), 1)
    _frame_count: list[int] = [0]

    def make_frame(t: float):
        if cancel_event is not None and cancel_event.is_set():
            raise RenderCancelled
        actual_t = t + preview_start if preview else t
        bg = bg_frame_getter(actual_t) if bg_frame_getter is not None else None
        result = animation.make_frame(actual_t, renderer, background=bg)
        _frame_count[0] += 1
        if progress_callback is not None:
            progress_callback(min(_frame_count[0], total_frames), total_frames)
        return result

    # Build video clip
    audio_start = preview_start if preview else 0.0
    video = VideoClip(frame_function=make_frame, duration=total_duration)
    video = video.with_fps(fps)
    video = video.with_audio(audio.subclipped(audio_start, audio_start + total_duration))

    # Ensure output directory exists
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Export
    print(f"Exporting to {output_path}...")
    video.write_videofile(
        str(output_path),
        fps=fps,
        codec="libx264",
        audio_codec="aac",
        logger=logger,
    )

    print(f"Done! Video saved to {output_path}")
    return output_path
