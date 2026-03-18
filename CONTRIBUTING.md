# Contributing

Thanks for your interest in contributing to Lyric Video Generator!

## Prerequisites

- Python 3.10+
- [FFmpeg](https://ffmpeg.org/download.html) installed and on your `PATH`
- Git

## Local Setup

```bash
git clone https://github.com/CuWilliams/lyric-video-generator.git
cd lyric-video-generator

python3 -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate

pip install -e .
```

## Running the App

**CLI:**
```bash
lyric-video --song my-song
# or with explicit paths
lyric-video --lyrics input/lyrics/my-song.json --audio input/audio/my-song.mp3
```

**GUI:**
```bash
lyric-video-gui
```

Input files go in:
- `input/lyrics/` — JSON lyric files
- `input/audio/` — audio files (MP3, WAV, etc.)
- `input/backgrounds/` — optional background video/image

See the [README](README.md) and [GUIDE](GUIDE.md) for full usage details and theme schema documentation.

## Submitting a Pull Request

1. Fork the repo and create a branch from `main`.
2. Make your changes. Keep commits focused — one logical change per commit.
3. Describe what your PR does and why in the PR description.
4. Open the PR against `main`.

There is no automated test suite at this time, so please manually verify your changes work end-to-end with both the CLI and GUI before submitting.

## Reporting Issues

Use the [GitHub issue tracker](https://github.com/CuWilliams/lyric-video-generator/issues). Include:
- What you were trying to do
- What happened vs. what you expected
- Your OS, Python version, and FFmpeg version
