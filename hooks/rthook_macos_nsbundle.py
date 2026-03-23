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
