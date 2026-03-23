"""
py2app build script for LV-Gen (macOS .app bundle).

Usage:
    pip install py2app
    python setup_py2app.py py2app

Output: dist/LV-Gen.app
"""
from setuptools import setup

# py2app 0.28 raises an error if install_requires is set on the distribution,
# but setuptools auto-populates it from pyproject.toml. Clear it before py2app
# reads it — py2app bundles deps from the venv rather than installing them.
import py2app.build_app as _py2app_build
_orig_finalize = _py2app_build.py2app.finalize_options
def _patched_finalize(self):
    self.distribution.install_requires = []
    _orig_finalize(self)
_py2app_build.py2app.finalize_options = _patched_finalize

APP = ["src/gui/main.py"]

DATA_FILES = [
    ("themes", ["themes/default.json"]),
    ("input/audio", ["input/audio/.gitkeep"]),
    ("input/lyrics", ["input/lyrics/.gitkeep"]),
    ("input/backgrounds", ["input/backgrounds/.gitkeep"]),
]

OPTIONS = {
    "argv_emulation": False,        # Must be False for PyQt6
    "iconfile": "assets/icon.icns", # Place icon here before building
    "plist": {
        "CFBundleName": "LV-Gen",
        "CFBundleDisplayName": "LV-Gen",
        "CFBundleIdentifier": "com.durtnurs.lv-gen",
        "CFBundleVersion": "1.0.0",
        "CFBundleShortVersionString": "1.0.0",
        "NSHighResolutionCapable": True,
        "NSRequiresAquaSystemAppearance": False,
        "NSPrincipalClass": "NSApplication",
        "LSMinimumSystemVersion": "11.0",
    },
    "packages": [
        "src",
        "src.cli",
        "src.core",
        "src.animations",
        "src.gui",
        "src.gui.panels",
        "PyQt6",
        "moviepy",
        "PIL",
        "numpy",
        "click",
        "imageio_ffmpeg",
    ],
    "excludes": [
        "PyQt6.QtLocation",
        "PyQt6.QtPositioning",
        "PyQt6.QtSensors",
        "PyQt6.QtWebEngineCore",
        "PyQt6.QtWebEngineWidgets",
        "PyInstaller",
        "tkinter",
        "test",
        "unittest",
    ],
}

setup(
    name="LV-Gen",
    app=APP,
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
)
