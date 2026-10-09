#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PYTHON="$ROOT/.venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  PYTHON="${PYTHON:-python3}"
fi

echo "Installing PyInstaller…"
"$PYTHON" -m pip install -q "pyinstaller>=6.0"

echo "Building FaceLES (Ubuntu onedir)…"
rm -rf "$ROOT/build" "$ROOT/dist/FaceLES"
"$PYTHON" -m PyInstaller --noconfirm --clean "$ROOT/packaging/FaceLES.spec"

DIST="$ROOT/dist/FaceLES"
cp "$ROOT/packaging/linux/run-faceles.sh" "$DIST/Run FaceLES.sh"
cp "$ROOT/packaging/linux/README.txt" "$DIST/README.txt"
chmod +x "$DIST/FaceLES" "$DIST/Run FaceLES.sh"

cat > "$DIST/FaceLES.desktop" <<EOF
[Desktop Entry]
Type=Application
Version=1.0
Name=FaceLES
Comment=Face login and attendance
Exec=$DIST/FaceLES
Path=$DIST
Icon=$DIST/_internal/assets/icons/app.svg
Terminal=false
Categories=Office;
StartupNotify=true
EOF
chmod +x "$DIST/FaceLES.desktop"

echo
echo "Built: $DIST/FaceLES"
echo "Run:   $DIST/FaceLES"
echo "Or:    $DIST/Run FaceLES.sh"
ls -lh "$DIST/FaceLES"

echo
echo "Packaging .deb for double-click install…"
"$ROOT/scripts/build_ubuntu_deb.sh"
