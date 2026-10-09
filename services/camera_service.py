"""Shared camera discovery and capture — one VideoCapture owner at a time."""
from __future__ import annotations

import os
import time
from typing import Callable

import cv2
import numpy as np
from PySide6.QtCore import QMutex, QMutexLocker, QObject, QThread, Signal

from config import settings
from services import storage_service


def pretty_camera_name(index: int) -> str:
    path = f"/sys/class/video4linux/video{index}/name"
    try:
        with open(path) as handle:
            raw = handle.read().strip()
    except OSError:
        return f"Camera {index}"
    low = raw.lower()
    if "logitech" in low or "046d" in low:
        return "Logitech camera"
    if "integrated" in low or "built-in" in low or "builtin" in low:
        return "Built-in webcam"
    if low.startswith("uvc"):
        return "USB camera"
    if ":" in raw and "(" not in raw:
        raw = raw.split(":", 1)[0].strip()
    name = raw.replace("_", " ").strip()
    return name or f"Camera {index}"


def capture_device_indexes() -> list[int]:
    base = "/sys/class/video4linux"
    found: list[int] = []
    if os.path.isdir(base):
        for entry in sorted(os.listdir(base)):
            if not entry.startswith("video"):
                continue
            try:
                index = int(entry[5:])
            except ValueError:
                continue
            node = 0
            try:
                with open(os.path.join(base, entry, "index")) as handle:
                    node = int(handle.read().strip())
            except (OSError, ValueError):
                node = 0
            if node == 0:
                found.append(index)
    return found or list(range(6))


def open_camera(index: int = 0) -> cv2.VideoCapture | None:
    for backend in (cv2.CAP_V4L2, cv2.CAP_ANY):
        cap = cv2.VideoCapture(index, backend)
        if cap.isOpened():
            return cap
        cap.release()
    return None


def discover_cameras() -> list[dict]:
    cameras: list[dict] = []
    for index in capture_device_indexes():
        cap = open_camera(index)
        if cap is None:
            continue
        try:
            ok, frame = False, None
            for _ in range(8):
                ok, frame = cap.read()
                if ok and frame is not None:
                    break
                time.sleep(0.05)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        finally:
            cap.release()
        if not ok or frame is None:
            continue
        cameras.append(
            {
                "index": index,
                "label": pretty_camera_name(index),
                "size": (width, height),
            }
        )
    counts: dict[str, int] = {}
    for cam in cameras:
        counts[cam["label"]] = counts.get(cam["label"], 0) + 1
    seen: dict[str, int] = {}
    for cam in cameras:
        if counts[cam["label"]] > 1:
            seen[cam["label"]] = seen.get(cam["label"], 0) + 1
            cam["label"] = f"{cam['label']} {seen[cam['label']]}"
    return cameras


class CameraWorker(QThread):
    """Owns a single VideoCapture and emits BGR frames."""

    frame_ready = Signal(object)  # numpy ndarray BGR
    status = Signal(str)
    failed = Signal(str)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._index = 0
        self._running = False
        self._mutex = QMutex()
        self._cap: cv2.VideoCapture | None = None

    def configure(self, index: int) -> None:
        with QMutexLocker(self._mutex):
            self._index = index

    def run(self) -> None:
        with QMutexLocker(self._mutex):
            index = self._index
        self._running = True
        self.status.emit("Starting camera…")
        cap = open_camera(index)
        if cap is None or not cap.isOpened():
            self.failed.emit("Camera unavailable")
            self._running = False
            return
        with QMutexLocker(self._mutex):
            self._cap = cap
        self.status.emit("Camera is on")
        while self._running:
            ok, frame = cap.read()
            if not ok or frame is None:
                time.sleep(0.05)
                continue
            self.frame_ready.emit(frame.copy())
            time.sleep(0.03)
        try:
            cap.release()
        except Exception:
            pass
        with QMutexLocker(self._mutex):
            self._cap = None

    def stop(self) -> None:
        self._running = False
        self.wait(2000)


class _DiscoverThread(QThread):
    finished_ok = Signal(list)

    def run(self) -> None:
        self.finished_ok.emit(discover_cameras())


class CameraService(QObject):
    """Application-wide camera coordinator."""

    cameras_updated = Signal(list)
    frame_ready = Signal(object)
    status_changed = Signal(str)
    camera_failed = Signal(str)
    index_changed = Signal(int)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self.cameras: list[dict] = []
        self.camera_index = storage_service.load_camera_pref()
        self._worker: CameraWorker | None = None
        self._discover: _DiscoverThread | None = None
        self._frame_hooks: list[Callable[[np.ndarray], None]] = []

    def active_index(self) -> int:
        return 0 if self.camera_index is None else self.camera_index

    def is_live(self) -> bool:
        return (
            bool(self.cameras)
            and self.camera_index is not None
            and self._worker is not None
            and self._worker.isRunning()
        )

    def refresh_cameras(self) -> None:
        if self._discover is not None and self._discover.isRunning():
            return
        self.status_changed.emit("Looking for cameras…")
        thread = _DiscoverThread(self)
        thread.finished_ok.connect(self._on_discovered)
        self._discover = thread
        thread.start()

    def _on_discovered(self, cameras: list) -> None:
        self.cameras = cameras
        if not cameras:
            self.camera_index = None
            self.cameras_updated.emit([])
            self.camera_failed.emit("No camera found")
            return
        chosen = 0
        if self.camera_index is not None:
            for i, cam in enumerate(cameras):
                if cam["index"] == self.camera_index:
                    chosen = i
                    break
        self.camera_index = cameras[chosen]["index"]
        storage_service.save_camera_pref(self.camera_index)
        self.cameras_updated.emit(cameras)
        self.index_changed.emit(self.camera_index)
        if self._worker is None or not self._worker.isRunning():
            self.start_preview()

    def select_index(self, index: int) -> None:
        if index == self.camera_index and self._worker and self._worker.isRunning():
            return
        self.camera_index = index
        storage_service.save_camera_pref(index)
        self.index_changed.emit(index)
        self.start_preview()

    def select_by_label(self, label: str) -> None:
        for cam in self.cameras:
            if cam["label"] == label:
                self.select_index(cam["index"])
                return

    def start_preview(self) -> None:
        self.stop_preview()
        if self.camera_index is None:
            self.camera_failed.emit("No camera selected")
            return
        worker = CameraWorker(self)
        worker.configure(self.camera_index)
        worker.frame_ready.connect(self._on_frame)
        worker.status.connect(self.status_changed.emit)
        worker.failed.connect(self.camera_failed.emit)
        self._worker = worker
        worker.start()

    def stop_preview(self) -> None:
        if self._worker is not None:
            self._worker.stop()
            self._worker = None

    def _on_frame(self, frame: np.ndarray) -> None:
        self.frame_ready.emit(frame)
        for hook in list(self._frame_hooks):
            try:
                hook(frame)
            except Exception:
                pass

    def add_frame_hook(self, hook: Callable[[np.ndarray], None]) -> None:
        if hook not in self._frame_hooks:
            self._frame_hooks.append(hook)

    def remove_frame_hook(self, hook: Callable[[np.ndarray], None]) -> None:
        if hook in self._frame_hooks:
            self._frame_hooks.remove(hook)

    def shutdown(self) -> None:
        self._frame_hooks.clear()
        self.stop_preview()
        if self._discover is not None and self._discover.isRunning():
            self._discover.wait(1500)
        self._discover = None
