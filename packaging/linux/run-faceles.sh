#!/usr/bin/env bash
# Double-click or run this. Keep it next to the FaceLES binary.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE"
chmod +x "$HERE/FaceLES" 2>/dev/null || true
exec "$HERE/FaceLES" "$@"
