import os

for key in ("QT_PLUGIN_PATH", "QT_QPA_PLATFORM_PLUGIN_PATH"):
    value = os.environ.get(key, "")
    if "cv2" in value or "opencv" in value.lower():
        os.environ.pop(key, None)
