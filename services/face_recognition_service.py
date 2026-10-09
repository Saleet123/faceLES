"""OpenCV Haar + LBPH face enrollment and matching — same rules as Ubuntu.tkinter.py."""
from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np

from config import settings


@dataclass
class FaceAssessment:
    ok: bool
    message: str
    face_roi: Optional[np.ndarray] = None
    confidence: Optional[float] = None


class FaceRecognitionService:
    def __init__(self) -> None:
        self.cascade = cv2.CascadeClassifier(settings.resource_path("haarcascade_frontalface_default.xml"))
        if self.cascade.empty():
            self.cascade = cv2.CascadeClassifier(settings.CASCADE_FILE)
        self.recognizer = None
        self.label_map: dict[int, str] = {}
        self._load_model()

    def model_exists(self) -> bool:
        return os.path.exists(settings.MODEL_FILE)

    def _load_model(self) -> None:
        self.recognizer = None
        self.label_map = {}
        if not self.model_exists():
            return
        recognizer = cv2.face.LBPHFaceRecognizer_create()
        recognizer.read(settings.MODEL_FILE)
        self.recognizer = recognizer
        if os.path.exists(settings.LABEL_MAP_FILE):
            with open(settings.LABEL_MAP_FILE) as handle:
                for line in handle:
                    parts = line.strip().split(":")
                    if len(parts) == 2:
                        self.label_map[int(parts[0])] = parts[1]

    def detect_faces(self, gray: np.ndarray, *, lenient: bool = False):
        if lenient:
            return self.cascade.detectMultiScale(gray, 1.1, 3, minSize=(40, 40))
        return self.cascade.detectMultiScale(gray, 1.2, 5, minSize=(60, 60))

    def assess_face(self, gray: np.ndarray, faces) -> FaceAssessment:
        if len(faces) == 0:
            return FaceAssessment(False, "No face detected — center yourself in the circle.")
        if len(faces) > 1:
            return FaceAssessment(False, "Multiple faces detected — only one person please.")
        x, y, w, h = faces[0]
        face = gray[y : y + h, x : x + w]
        brightness = float(np.mean(face))
        h_img, w_img = gray.shape[:2]
        cx, cy = x + w / 2, y + h / 2
        centered = abs(cx - w_img / 2) < w_img * 0.22 and abs(cy - h_img / 2) < h_img * 0.22
        large_enough = w >= 90 and h >= 90
        if brightness < 45 or brightness > 210:
            return FaceAssessment(False, "Poor lighting or angle — adjust position.")
        if not large_enough or not centered:
            return FaceAssessment(False, "Poor lighting or angle — adjust position.")
        # Same 200×200 size used when training the LBPH model.
        return FaceAssessment(True, "Hold still… capturing", cv2.resize(face, (200, 200)))

    @staticmethod
    def _face_for_predict(face_gray: np.ndarray) -> np.ndarray:
        """LBPH was trained on 200×200 crops — always predict at that size."""
        if face_gray.shape[0] == 200 and face_gray.shape[1] == 200:
            return face_gray
        return cv2.resize(face_gray, (200, 200))

    def match_face(self, face_roi: np.ndarray, threshold: float | None = None) -> FaceAssessment:
        threshold = settings.LBPH_LOGIN_THRESHOLD if threshold is None else threshold
        if self.recognizer is None:
            self._load_model()
        if self.recognizer is None:
            return FaceAssessment(False, "No face model enrolled.")
        prepared = self._face_for_predict(face_roi)
        _id, confidence = self.recognizer.predict(prepared)
        if confidence < threshold:
            name = self.label_map.get(_id, settings.VALID_USERNAME)
            return FaceAssessment(True, f"Matched {name}", face_roi, float(confidence))
        return FaceAssessment(False, "Looking for a match…", face_roi, float(confidence))

    def presence_match(self, gray: np.ndarray) -> bool:
        recognized, _boxes = self.presence_evaluate(gray)
        return recognized

    def presence_evaluate(
        self, gray: np.ndarray, *, lenient: bool = False
    ) -> tuple[bool, list[tuple[int, int, int, int, bool]]]:
        """
        Detect faces and score presence.

        Returns (any_recognized, boxes) where each box is
        (x, y, w, h, recognized) in grayscale/frame coordinates.
        """
        if self.recognizer is None:
            self._load_model()
        faces = self.detect_faces(gray, lenient=lenient)
        boxes: list[tuple[int, int, int, int, bool]] = []
        any_ok = False
        if self.recognizer is None:
            for (x, y, w, h) in faces:
                boxes.append((int(x), int(y), int(w), int(h), False))
            return False, boxes
        for (x, y, w, h) in faces:
            crop = gray[y : y + h, x : x + w]
            if crop.size == 0:
                continue
            prepared = self._face_for_predict(crop)
            _id, confidence = self.recognizer.predict(prepared)
            # LBPH: lower distance = better match
            ok = float(confidence) < settings.LBPH_PRESENCE_THRESHOLD
            if ok:
                any_ok = True
            boxes.append((int(x), int(y), int(w), int(h), bool(ok)))
        return any_ok, boxes

    def train_and_save(self, faces: list[np.ndarray], username: str | None = None) -> None:
        if len(faces) < settings.ENROLL_TARGET:
            raise ValueError("Not enough faces captured.")
        username = username or settings.VALID_USERNAME
        recognizer = cv2.face.LBPHFaceRecognizer_create()
        recognizer.train(faces, np.array([0] * len(faces)))
        recognizer.save(settings.MODEL_FILE)
        with open(settings.LABEL_MAP_FILE, "w") as handle:
            handle.write(f"0:{username}\n")
        self._load_model()

    def process_bgr(self, frame_bgr: np.ndarray) -> tuple[FaceAssessment, object]:
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        faces = self.detect_faces(gray)
        assessment = self.assess_face(gray, faces)
        return assessment, faces
