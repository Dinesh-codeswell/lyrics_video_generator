"""GUI entry point for lyric-video-generator."""

import sys
from pathlib import Path

# On macOS, QtCore.abi3.so contains a C++ static initializer that calls
# CFBundleGetMainBundle() the moment the library is dlopen'd. On macOS 26+,
# if that call returns NULL (which happens before NSApplication is set up in
# a py2app bundle launched via Finder/launchd), CoreFoundation's PAC
# signature check crashes with SIGSEGV.
# Calling [NSApplication sharedApplication] here registers the main bundle
# before any Qt module is imported. NSApplicationLoad() is deprecated macOS
# 12+ and is a no-op on macOS 26; this approach works on all versions.
if sys.platform == "darwin":
    try:
        import ctypes
        import ctypes.util
        _libobjc = ctypes.cdll.LoadLibrary(ctypes.util.find_library("objc"))
        _libobjc.objc_getClass.restype = ctypes.c_void_p
        _libobjc.objc_getClass.argtypes = [ctypes.c_char_p]
        _libobjc.sel_registerName.restype = ctypes.c_void_p
        _libobjc.sel_registerName.argtypes = [ctypes.c_char_p]
        _libobjc.objc_msgSend.restype = ctypes.c_void_p
        _libobjc.objc_msgSend.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        ctypes.cdll.LoadLibrary(ctypes.util.find_library("AppKit"))
        _NSApplication = _libobjc.objc_getClass(b"NSApplication")
        _sel = _libobjc.sel_registerName(b"sharedApplication")
        _libobjc.objc_msgSend(_NSApplication, _sel)
    except Exception:
        pass

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from src.gui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Lyric Video Generator")
    _icon_path = Path(__file__).parents[2] / "assets" / "icon.png"
    if _icon_path.exists():
        app.setWindowIcon(QIcon(str(_icon_path)))
    app.setStyleSheet("""
        QGroupBox {
            font-size: 14pt;
            font-weight: 600;
            margin-top: 26px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            left: 10px;
            top: 4px;
            padding: 0 4px;
        }
    """)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
