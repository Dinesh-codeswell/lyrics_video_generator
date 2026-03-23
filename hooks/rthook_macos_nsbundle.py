"""
Runtime hook: initialize NSApplication before Qt loads on macOS.

QtCore.abi3.so contains a C++ static initializer (qdarwinpermissionplugin_location.mm)
that calls CFBundleGetMainBundle() the moment the library is dlopen'd. On macOS 26+,
if that call returns NULL (which it does before NSApplication is set up in a PyInstaller
bundle), CoreFoundation's PAC signature check crashes with SIGSEGV.

Loading AppKit and calling NSApplicationLoad() here ensures the main bundle is registered
before any Qt module is imported.
"""
import sys

if sys.platform == "darwin":
    try:
        import ctypes
        import ctypes.util
        _appkit = ctypes.cdll.LoadLibrary(ctypes.util.find_library("AppKit"))
        _appkit.NSApplicationLoad()
    except Exception:
        pass
