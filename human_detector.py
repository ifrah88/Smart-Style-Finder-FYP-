"""
Human (person) detection gate for uploaded query photos, using YOLO.

A user must upload a photo of a person wearing an outfit. If YOLO does not
detect a person, the image is rejected and is NOT passed to the colour / search
model (this stops non-fashion images like flags, scenery, objects from returning
dress suggestions).

Public API:
    has_person(image_path) -> (bool, float)   # detected?, best person confidence
    available() -> bool
"""
from __future__ import annotations

import os
import threading
from typing import Optional, Tuple

MODEL_NAME = "yolov8n.pt"  # nano: tiny + fast, downloads once
PERSON_CLASS = 0           # COCO 'person'
CONF_THRESHOLD = 0.40      # min confidence to count as a person

# keep the weights with the project so it's portable / offline
_LOCAL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")


class _Detector:
    _inst: Optional["_Detector"] = None
    _lock = threading.Lock()

    def __init__(self):
        self._model = None
        self._err: Optional[str] = None

    @classmethod
    def get(cls) -> "_Detector":
        if cls._inst is None:
            with cls._lock:
                if cls._inst is None:
                    cls._inst = cls()
        return cls._inst

    def _ensure(self) -> bool:
        if self._model is not None:
            return True
        if self._err is not None:
            return False
        try:
            from ultralytics import YOLO
            os.makedirs(_LOCAL_DIR, exist_ok=True)
            local = os.path.join(_LOCAL_DIR, MODEL_NAME)
            self._model = YOLO(local if os.path.exists(local) else MODEL_NAME)
            # cache the weights into the project for portability
            if not os.path.exists(local):
                try:
                    src = getattr(self._model, "ckpt_path", None)
                    if src and os.path.exists(src):
                        import shutil
                        shutil.copy(src, local)
                except Exception:
                    pass
            return True
        except Exception as exc:  # noqa: BLE001
            self._err = f"{type(exc).__name__}: {exc}"
            return False

    def detect(self, image_path: str) -> Tuple[bool, float]:
        if not self._ensure():
            raise RuntimeError(f"YOLO unavailable: {self._err}")
        res = self._model.predict(image_path, verbose=False, conf=CONF_THRESHOLD)
        best = 0.0
        for r in res:
            for b in r.boxes:
                if int(b.cls[0]) == PERSON_CLASS:
                    best = max(best, float(b.conf[0]))
        return best >= CONF_THRESHOLD, best


def available() -> bool:
    return _Detector.get()._ensure()


def has_person(image_path: str) -> Tuple[bool, float]:
    return _Detector.get().detect(image_path)
