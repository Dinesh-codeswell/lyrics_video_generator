"""Auto-match song files from the input/ directory structure."""

from dataclasses import dataclass
from pathlib import Path

import click

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

INPUT_AUDIO_DIR = PROJECT_ROOT / "input" / "audio"
INPUT_LYRICS_DIR = PROJECT_ROOT / "input" / "lyrics"
INPUT_BACKGROUNDS_DIR = PROJECT_ROOT / "input" / "backgrounds"

AUDIO_EXTENSIONS = (".mp3", ".wav")


@dataclass
class SongInfo:
    name: str
    has_lyrics: bool
    has_audio: bool
    has_background: bool

    @property
    def is_loadable(self) -> bool:
        return self.has_lyrics and self.has_audio


def scan_songs() -> list[SongInfo]:
    """Scan input/ directories and return all discovered songs.

    A song is discovered if it has at least a lyrics JSON or an audio file.
    Returns a list sorted by song name.
    """
    names: set[str] = set()
    for p in INPUT_LYRICS_DIR.glob("*.json"):
        names.add(p.stem)
    for ext in AUDIO_EXTENSIONS:
        for p in INPUT_AUDIO_DIR.glob(f"*{ext}"):
            names.add(p.stem)

    songs = []
    for name in sorted(names):
        songs.append(SongInfo(
            name=name,
            has_lyrics=(INPUT_LYRICS_DIR / f"{name}.json").exists(),
            has_audio=_find_audio(name) is not None,
            has_background=(INPUT_BACKGROUNDS_DIR / f"{name}.mp4").exists(),
        ))
    return songs


def resolve_song(
    song_name: str,
    lyrics_override: str | None = None,
    audio_override: str | None = None,
    background_override: str | None = None,
    no_background: bool = False,
) -> dict[str, Path | None]:
    """Resolve file paths for a song by name from the input/ directories.

    Args:
        song_name: Base name of the song (e.g. 'disciples_of_dysfunction').
        lyrics_override: Explicit lyrics path (overrides auto-match).
        audio_override: Explicit audio path (overrides auto-match).
        background_override: Explicit background path (overrides auto-match).
        no_background: If True, force no background video.

    Returns:
        Dict with keys 'lyrics', 'audio', 'background' mapped to resolved Paths.
        'background' may be None if not found or disabled.
    """
    # Resolve lyrics
    if lyrics_override:
        lyrics_path = Path(lyrics_override)
    else:
        lyrics_path = INPUT_LYRICS_DIR / f"{song_name}.json"
        if not lyrics_path.exists():
            raise click.UsageError(
                f"Lyrics file not found: {lyrics_path}\n"
                f"Place your lyrics JSON at: input/lyrics/{song_name}.json"
            )

    # Resolve audio
    if audio_override:
        audio_path = Path(audio_override)
    else:
        audio_path = _find_audio(song_name)
        if audio_path is None:
            extensions = ", ".join(AUDIO_EXTENSIONS)
            raise click.UsageError(
                f"Audio file not found for '{song_name}' in {INPUT_AUDIO_DIR}\n"
                f"Place your audio file at: input/audio/{song_name}.mp3 (supported: {extensions})"
            )

    # Resolve background
    background_path: Path | None = None
    if no_background:
        background_path = None
    elif background_override:
        background_path = Path(background_override)
    else:
        candidate = INPUT_BACKGROUNDS_DIR / f"{song_name}.mp4"
        if candidate.exists():
            background_path = candidate

    return {
        "lyrics": lyrics_path,
        "audio": audio_path,
        "background": background_path,
    }


def _find_audio(song_name: str) -> Path | None:
    """Search for an audio file matching the song name."""
    for ext in AUDIO_EXTENSIONS:
        candidate = INPUT_AUDIO_DIR / f"{song_name}{ext}"
        if candidate.exists():
            return candidate
    return None
