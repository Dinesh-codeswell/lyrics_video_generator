# PyInstaller spec for Lyric Video Generator (macOS)
#
# Usage:
#   pip install pyinstaller
#   pyinstaller build.spec
#
# Output: dist/Lyric Video Generator.app
#
# Prerequisites:
#   - Place your app icon at assets/icon.icns before building
#   - Run from the repo root with your venv active

import sys
from pathlib import Path

block_cipher = None

# Data files to bundle with the app
datas = [
    # Default theme
    ("themes/default.json", "themes"),
    # Input folder structure (empty dirs with .gitkeep)
    ("input/audio/.gitkeep",      "input/audio"),
    ("input/lyrics/.gitkeep",     "input/lyrics"),
    ("input/backgrounds/.gitkeep","input/backgrounds"),
]

a = Analysis(
    ["src/gui/main.py"],
    pathex=["."],
    binaries=[],
    datas=datas,
    hiddenimports=[
        # PyQt6 plugins that PyInstaller misses
        "PyQt6.QtMultimedia",
        "PyQt6.QtMultimediaWidgets",
        "PyQt6.sip",
        # imageio-ffmpeg — ensures bundled FFmpeg binary is found
        "imageio_ffmpeg",
        # moviepy internals
        "moviepy",
        "moviepy.video.io.VideoFileClip",
        "moviepy.audio.io.AudioFileClip",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=["hooks/rthook_macos_nsbundle.py"],
    excludes=[
        # These Qt plugins crash on macOS when bundled by PyInstaller —
        # they call CFBundleCopyBundleURL during init which fails in the
        # PyInstaller app context (qdarwinpermissionplugin SIGSEGV)
        "PyQt6.QtLocation",
        "PyQt6.QtPositioning",
        "PyQt6.QtSensors",
        "PyQt6.QtWebEngineCore",
        "PyQt6.QtWebEngineWidgets",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="LV-Gen",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,          # No terminal window on launch
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="LV-Gen",
)

app = BUNDLE(
    coll,
    name="LV-Gen.app",
    icon="assets/icon.icns",    # Place your icon here before building
    bundle_identifier="com.durtnurs.lv-gen",
    info_plist={
        "NSHighResolutionCapable": True,
        "NSRequiresAquaSystemAppearance": False,  # Allows dark mode
        "NSPrincipalClass": "NSApplication",      # Ensures CFBundleGetMainBundle() is valid at Qt init
        "CFBundleShortVersionString": "1.0.0",
        "CFBundleVersion": "1",
        "LSMinimumSystemVersion": "11.0",         # macOS Big Sur+
    },
)
