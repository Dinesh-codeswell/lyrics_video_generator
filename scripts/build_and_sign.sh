#!/usr/bin/env bash
# build_and_sign.sh — Build, post-process, sign, and install LV-Gen.app
#
# Usage (from repo root, venv active):
#   bash scripts/build_and_sign.sh
#
# Requires:
#   - venv active (source venv/bin/activate)
#   - Developer ID Application certificate in Keychain
#   - SIGN_CERT env var set to your Developer ID certificate hash
#     e.g. export SIGN_CERT="$(security find-identity -v -p codesigning | grep 'Developer ID' | awk '{print $2}')"

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CERT="${SIGN_CERT:?Error: SIGN_CERT env var not set. Export your Developer ID certificate hash before running.}"
ENT="$REPO_ROOT/entitlements.plist"
DIST="$REPO_ROOT/dist/LV-Gen.app"
INSTALL="/Applications/LV-Gen.app"

echo "=== 1. Build py2app bundle ==="
cd "$REPO_ROOT"
python setup_py2app.py py2app

echo "=== 2. Post-process bundle ==="

# Remove dist-info dirs (confuse codesign)
find "$DIST" -name "*.dist-info" -type d -exec rm -rf {} + 2>/dev/null || true

# Remove Tcl/Tk data (app doesn't use tkinter)
for d in _tcl_data _tk_data tcl8; do
  rm -rf "$DIST/Contents/Frameworks/$d" "$DIST/Contents/Resources/$d" 2>/dev/null || true
done

# Remove hidden .dylibs from Frameworks (codesign rejects them)
find "$DIST/Contents/Frameworks" -name ".dylibs" -type d -exec rm -rf {} + 2>/dev/null || true

# Rename PIL's .dylibs → _dylibs (hidden dirs excluded from codesign seal)
PYVER=$(ls "$DIST/Contents/Resources/lib/" | head -1)  # e.g. python3.13
PILDIR="$DIST/Contents/Resources/lib/$PYVER/PIL"
if [ -d "$PILDIR/.dylibs" ]; then
  mv "$PILDIR/.dylibs" "$PILDIR/_dylibs"
  echo "  Renamed PIL/.dylibs -> PIL/_dylibs"

  # Update @loader_path/.dylibs/ references in .so files to @loader_path/_dylibs/
  for f in "$PILDIR"/*.so; do
    for lib in "$PILDIR/_dylibs"/*.dylib; do
      libname=$(basename "$lib")
      install_name_tool -change \
        "@loader_path/.dylibs/$libname" \
        "@loader_path/_dylibs/$libname" \
        "$f" 2>/dev/null || true
    done
  done
  echo "  Updated .so @loader_path references"
fi

# Symlink base_library.zip: move to Resources, symlink from Frameworks
if [ -f "$DIST/Contents/Frameworks/base_library.zip" ]; then
  mv "$DIST/Contents/Frameworks/base_library.zip" "$DIST/Contents/Resources/base_library.zip"
  ln -s "../Resources/base_library.zip" "$DIST/Contents/Frameworks/base_library.zip"
  echo "  Symlinked base_library.zip"
fi

echo "=== 3. Sign all binaries ==="

# Sign dylibs (including _dylibs)
find "$DIST" -name "*.dylib" \
  -exec codesign --force --sign "$CERT" --options runtime --entitlements "$ENT" {} \; 2>/dev/null
echo "  Dylibs signed"

# Sign .so extension modules
find "$DIST" -name "*.so" \
  -exec codesign --force --sign "$CERT" --options runtime --entitlements "$ENT" {} \; 2>/dev/null
echo "  .so files signed"

# Sign extension-less Mach-O files in Frameworks (Qt dylibs without .dylib extension)
find "$DIST/Contents/Frameworks" -maxdepth 1 -type f | while read f; do
  if file "$f" 2>/dev/null | grep -q "Mach-O"; then
    codesign --force --sign "$CERT" --options runtime --entitlements "$ENT" "$f" 2>/dev/null
  fi
done
echo "  Extension-less Mach-O files signed"

echo "=== 4. Sign bundle ==="
codesign --force --sign "$CERT" --options runtime --entitlements "$ENT" "$DIST"
echo "  Bundle signed"

# Verify
codesign -dv "$DIST" 2>&1 | grep -E "TeamIdentifier|Sealed Resources"

echo "=== 5. Install to /Applications ==="
rm -rf "$INSTALL"
cp -r "$DIST" "$INSTALL"
echo "  Installed: $INSTALL"

echo ""
echo "Done. Launch /Applications/LV-Gen.app from Finder to test."
