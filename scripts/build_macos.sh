#!/usr/bin/env bash
# Build FaceLES.app on macOS. Must be run on a Mac.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "This script must run on a Mac."
  exit 1
fi

PYTHON="$ROOT/.venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  python3 -m venv "$ROOT/.venv"
  PYTHON="$ROOT/.venv/bin/python"
fi

echo "Installing dependencies…"
"$PYTHON" -m pip install -q -r "$ROOT/requirements.txt" "pyinstaller>=6.0"

ICONSET="$ROOT/build/app.iconset"
ICNS="$ROOT/assets/icons/app.icns"
if command -v iconutil >/dev/null 2>&1; then
  rm -rf "$ICONSET"
  mkdir -p "$ICONSET"
  for size in 16 32 128 256; do
    src="$ROOT/assets/icons/app-${size}.png"
    if [[ -f "$src" ]]; then
      cp "$src" "$ICONSET/icon_${size}x${size}.png"
    fi
  done
  if [[ -f "$ROOT/assets/icons/app-32.png" ]]; then
    cp "$ROOT/assets/icons/app-32.png" "$ICONSET/icon_16x16@2x.png"
  fi
  if [[ -f "$ROOT/assets/icons/app-64.png" ]]; then
    cp "$ROOT/assets/icons/app-64.png" "$ICONSET/icon_32x32@2x.png"
  fi
  if [[ -f "$ROOT/assets/icons/app-256.png" ]]; then
    cp "$ROOT/assets/icons/app-256.png" "$ICONSET/icon_128x128@2x.png"
    cp "$ROOT/assets/icons/app-256.png" "$ICONSET/icon_256x256.png"
  fi
  iconutil -c icns "$ICONSET" -o "$ICNS" || true
fi

echo "Building FaceLES.app…"
rm -rf "$ROOT/build/FaceLES" "$ROOT/dist/FaceLES" "$ROOT/dist/FaceLES.app"
"$PYTHON" -m PyInstaller --noconfirm --clean "$ROOT/packaging/FaceLES.spec"

APP="$ROOT/dist/FaceLES.app"
if [[ ! -d "$APP" ]]; then
  echo "Build finished but FaceLES.app was not created. Check dist/"
  ls -la "$ROOT/dist"
  exit 1
fi

ZIP="$ROOT/dist/FaceLES-macOS.zip"
rm -f "$ZIP"
ditto -c -k --sequesterRsrc --keepParent "$APP" "$ZIP"

echo
echo "Built: $APP"
echo "Zip:   $ZIP"
echo "Give employees the .app (or the zip). They drag it to Applications, then open FaceLES."
echo "Unsigned apps: right-click → Open the first time (Gatekeeper)."
