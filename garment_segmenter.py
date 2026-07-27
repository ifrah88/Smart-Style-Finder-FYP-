"""
Garment segmentation for uploaded query photos.

Uses a clothes/human-parsing model (SegFormer fine-tuned on the ATR dataset,
`mattmdjaga/segformer_b2_clothes`) to mask ONLY the clothing pixels — excluding
background AND the person's skin / face / hair. This fixes background-colour
pollution when a user uploads a photo of someone wearing an outfit, and works on
Pakistani garments (kurta/shirt -> "upper-clothes/dress", shalwar -> "pants",
dupatta -> "scarf").

Public API:
    rgb01, mask = segment_garment(image_path)   # rgb float 0..1, bool mask
    available()                                  # True if the model loaded ok
"""
from __future__ import annotations

import threading
from typing import Optional, Tuple

import numpy as np
from PIL import Image

MODEL_ID = "mattmdjaga/segformer_b2_clothes"
# ATR label ids that are garments (drop background/skin/hair/shoes/bag)
GARMENT_IDS = {4, 5, 6, 7, 8, 17}  # Upper-clothes, Skirt, Pants, Dress, Belt, Scarf


class _Segmenter:
    _inst: Optional["_Segmenter"] = None
    _lock = threading.Lock()

    def __init__(self):
        self._proc = None
        self._model = None
        self._err: Optional[str] = None

    @classmethod
    def get(cls) -> "_Segmenter":
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
            import torch  # noqa
            from transformers import AutoModelForSemanticSegmentation, SegformerImageProcessor
            self._proc = SegformerImageProcessor.from_pretrained(MODEL_ID)
            self._model = AutoModelForSemanticSegmentation.from_pretrained(MODEL_ID).eval()
            return True
        except Exception as exc:  # noqa: BLE001
            self._err = f"{type(exc).__name__}: {exc}"
            return False

    def segment(self, image_path: str) -> Tuple[np.ndarray, np.ndarray]:
        import torch
        if not self._ensure():
            raise RuntimeError(f"garment segmenter unavailable: {self._err}")
        im = Image.open(image_path).convert("RGB")
        inp = self._proc(images=im, return_tensors="pt")
        with torch.no_grad():
            logits = self._model(**inp).logits
        up = torch.nn.functional.interpolate(
            logits, size=im.size[::-1], mode="bilinear", align_corners=False
        )
        lab = up.argmax(1)[0].cpu().numpy()
        mask = np.isin(lab, list(GARMENT_IDS))
        rgb = np.asarray(im, np.float32) / 255.0
        return rgb, mask


def available() -> bool:
    return _Segmenter.get()._ensure()


def segment_garment(image_path: str) -> Tuple[np.ndarray, np.ndarray]:
    """Return (rgb in 0..1, bool garment mask). Raises if the model is unavailable."""
    rgb, mask = _Segmenter.get().segment(image_path)
    # require a sensible amount of garment; otherwise signal failure to the caller
    if mask.mean() < 0.02:
        raise RuntimeError("no garment detected")
    return rgb, mask
