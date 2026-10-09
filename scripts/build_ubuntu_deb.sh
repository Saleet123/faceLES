#!/usr/bin/env bash
# Build a double-clickable Ubuntu .deb from the PyInstaller folder.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

VERSION="1.0.0"
ARCH="$(dpkg --print-architecture 2>/dev/null || echo amd64)"
PKG_NAME="faceles_${VERSION}_${ARCH}"
DIST="$ROOT/dist/FaceLES"
STAGE="$ROOT/build/deb/${PKG_NAME}"
DEB="$ROOT/dist/${PKG_NAME}.deb"

if [[ ! -x "$DIST/FaceLES" ]]; then
  echo "No app bundle yet — building it first…"
  "$ROOT/scripts/build_ubuntu.sh"
fi

echo "Staging Debian package…"
rm -rf "$ROOT/build/deb"
mkdir -p \
  "$STAGE/DEBIAN" \
  "$STAGE/opt/faceles" \
  "$STAGE/usr/bin" \
  "$STAGE/usr/share/applications" \
  "$STAGE/usr/share/icons/hicolor/scalable/apps"

cp -a "$DIST/FaceLES" "$DIST/_internal" "$STAGE/opt/faceles/"
chmod 755 "$STAGE/opt/faceles/FaceLES"

install -m 755 "$ROOT/packaging/deb/faceles-wrapper.sh" "$STAGE/usr/bin/faceles"
install -m 644 "$ROOT/packaging/deb/faceles.desktop" "$STAGE/usr/share/applications/faceles.desktop"

if [[ -f "$ROOT/assets/icons/app.svg" ]]; then
  install -m 644 "$ROOT/assets/icons/app.svg" "$STAGE/usr/share/icons/hicolor/scalable/apps/faceles.svg"
fi
for size in 16 24 32 48 64 128 256; do
  src="$ROOT/assets/icons/app-${size}.png"
  if [[ -f "$src" ]]; then
    mkdir -p "$STAGE/usr/share/icons/hicolor/${size}x${size}/apps"
    install -m 644 "$src" "$STAGE/usr/share/icons/hicolor/${size}x${size}/apps/faceles.png"
  fi
done
if [[ -f "$ROOT/assets/icons/app.png" ]]; then
  mkdir -p "$STAGE/usr/share/icons/hicolor/256x256/apps"
  install -m 644 "$ROOT/assets/icons/app.png" "$STAGE/usr/share/icons/hicolor/256x256/apps/faceles.png"
fi

SIZE_KB="$(du -sk "$STAGE" | awk '{print $1}')"
sed "s/^Installed-Size: 0$/Installed-Size: ${SIZE_KB}/" "$ROOT/packaging/deb/control" \
  > "$STAGE/DEBIAN/control"
install -m 755 "$ROOT/packaging/deb/postinst" "$STAGE/DEBIAN/postinst"
install -m 755 "$ROOT/packaging/deb/postrm" "$STAGE/DEBIAN/postrm"

echo "Building $DEB …"
rm -f "$DEB"
fakeroot dpkg-deb --root-owner-group --build "$STAGE" "$DEB"

echo
echo "Debian package:"
ls -lh "$DEB"
dpkg-deb --info "$DEB" | sed -n '1,20p'

DESKTOP="${HOME}/Desktop"
if [[ -d "$DESKTOP" ]]; then
  cp -f "$DEB" "$DESKTOP/${PKG_NAME}.deb"
  echo "Also copied to: $DESKTOP/${PKG_NAME}.deb"
  echo "Double-click that file to install."
fi
