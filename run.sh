#!/usr/bin/env bash
# Launch FaceLES (PySide6). Tk/Xft vendor preload is no longer required.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

PYTHON="$ROOT/.venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  PYTHON="python3"
fi

# Prevent OpenCV's bundled Qt plugins from shadowing PySide6.
unset QT_PLUGIN_PATH || true
export QT_QPA_PLATFORM_PLUGIN_PATH="$("$PYTHON" - <<'PY'
import os
import PySide6
print(os.path.join(os.path.dirname(PySide6.__file__), "Qt", "plugins"))
PY
)"

exec "$PYTHON" "$ROOT/main.py" "$@"
