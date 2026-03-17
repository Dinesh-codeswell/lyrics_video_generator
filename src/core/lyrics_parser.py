"""Lyrics JSON parser and validation."""

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class LyricLine:
    """A single timed lyric line."""
    text: str
    start_time: float
    end_time: float
    duration: float


def parse_lyrics(filepath: str | Path) -> dict:
    """Load and parse a lyrics JSON file.

    Args:
        filepath: Path to the lyrics JSON file.

    Returns:
        Dict with keys: title, artist, lines (list of LyricLine).

    Raises:
        FileNotFoundError: If the file doesn't exist.
        ValueError: If the JSON structure is invalid.
    """
    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"Lyrics file not found: {filepath}")

    with open(filepath, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {filepath}: {e}")

    _validate_structure(data, filepath)

    raw_lyrics = data["lyrics"]
    lines = _build_lyric_lines(raw_lyrics)

    return {
        "title": data["title"],
        "artist": data["artist"],
        "intro_end_time": data.get("intro_end_time"),    # float | None
        "outro_start_time": data.get("outro_start_time"),  # float | None
        "bpm": data.get("bpm"),                          # float | None
        "time_sig_num": data.get("time_sig_num"),        # int | None
        "beat_offset_s": data.get("beat_offset_s"),      # float | None
        "lines": lines,
    }


def _validate_structure(data: dict, filepath: Path) -> None:
    """Validate the top-level JSON structure."""
    if not isinstance(data, dict):
        raise ValueError(f"Expected a JSON object in {filepath}, got {type(data).__name__}")

    for key in ("title", "artist", "lyrics"):
        if key not in data:
            raise ValueError(f"Missing required key '{key}' in {filepath}")

    if not isinstance(data["lyrics"], list):
        raise ValueError(f"'lyrics' must be a list in {filepath}")

    if len(data["lyrics"]) < 2:
        raise ValueError(f"'lyrics' must have at least 2 entries (one line + end marker) in {filepath}")

    for i, entry in enumerate(data["lyrics"]):
        if not isinstance(entry, dict):
            raise ValueError(f"Lyric entry {i} must be an object in {filepath}")
        if "time" not in entry or "text" not in entry:
            raise ValueError(f"Lyric entry {i} missing 'time' or 'text' in {filepath}")
        if not isinstance(entry["time"], (int, float)):
            raise ValueError(f"Lyric entry {i} 'time' must be a number in {filepath}")
        if not isinstance(entry["text"], str):
            raise ValueError(f"Lyric entry {i} 'text' must be a string in {filepath}")


def _build_lyric_lines(raw_lyrics: list[dict]) -> list[LyricLine]:
    """Convert raw lyric entries into LyricLine objects with computed durations."""
    lines = []

    for i, entry in enumerate(raw_lyrics):
        # Skip the end marker (final empty text entry)
        if entry["text"] == "":
            continue

        start_time = entry["time"]

        # End time is the start of the next entry
        if i + 1 < len(raw_lyrics):
            end_time = raw_lyrics[i + 1]["time"]
        else:
            # Last line with no end marker — give it a default 3s duration
            end_time = start_time + 3.0

        duration = end_time - start_time

        lines.append(LyricLine(
            text=entry["text"],
            start_time=start_time,
            end_time=end_time,
            duration=duration,
        ))

    return lines
