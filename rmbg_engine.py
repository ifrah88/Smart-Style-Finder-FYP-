"""
Background removal engine using BRIA RMBG-2.0 (state-of-the-art salient object
segmentation). Falls back gracefully to rembg or no-op if the model can't be
loaded.

The exported helper returns (rgb_float[H,W,3] in 0..1, mask_bool[H,W], mode_str).
This matches the shape expected by color_picker_engine._foreground_rgb_mask.
"""

from __future__ import annotations

import os
import threading
from typing import Optional, Tuple

import numpy as np
from PIL import Image


_MODEL_LOCK = threading.Lock()
_MODEL = None
_TRANSFORM = None
_DEVICE = None
_LOAD_ERR: Optional[str] = None


def _try_load_rmbg() -> bool:
    """Lazy-load BRIA RMBG-2.0. Returns True on success."""
    global _MODEL, _TRANSFORM, _DEVICE, _LOAD_ERR
    if _MODEL is not None:
        return True
    with _MODEL_LOCK:
        if _MODEL is not None:
            return True
        try:
            import torch
            from torchvision import transforms
            from transformers import AutoModelForImageSegmentation

            device = "cuda" if torch.cuda.is_available() else "cpu"

            model = AutoModelForImageSegmentation.from_pretrained(
                "briaai/RMBG-2.0", trust_remote_code=True
            )
            # FP32 on CPU for stability; FP16 on GPU is fine but optional.
            model.to(device)
            model.eval()

            # Official preprocessing recipe from the model card.
            image_size = (1024, 1024)
            tform = transforms.Compose(
                [
                    transforms.Resize(image_size),
                    transforms.ToTensor(),
                    transforms.Normalize(
                        [0.485, 0.456, 0.406], [0.229, 0.224, 0.225]
                    ),
                ]
            )

            _MODEL = model
            _TRANSFORM = tform
            _DEVICE = device
            _LOAD_ERR = None
            return True
        except Exception as exc:  # noqa: BLE001
            _LOAD_ERR = f"{type(exc).__name__}: {exc}"
            _MODEL = None
            _TRANSFORM = None
            _DEVICE = None
            return False


def rmbg_load_error() -> Optional[str]:
    return _LOAD_ERR


def _alpha_from_rmbg(pil_rgb: Image.Image) -> Optional[np.ndarray]:
    if not _try_load_rmbg():
        return None
    import torch

    w, h = pil_rgb.size
    x = _TRANSFORM(pil_rgb).unsqueeze(0).to(_DEVICE)
    with torch.no_grad():
        out = _MODEL(x)
        # RMBG-2.0 returns list[Tensor] or Tensor depending on signature; handle both.
        if isinstance(out, (list, tuple)):
            pred = out[-1]
        else:
            pred = out
        if hasattr(pred, "sigmoid"):
            pred = pred.sigmoid()
        else:
            pred = torch.sigmoid(pred)
        mask = pred[0].squeeze().detach().cpu().numpy()

    mask_img = Image.fromarray((np.clip(mask, 0.0, 1.0) * 255.0).astype(np.uint8))
    mask_img = mask_img.resize((w, h), Image.Resampling.BILINEAR)
    return np.asarray(mask_img, dtype=np.float32) / 255.0


# Cached rembg session (avoids re-loading the model for every image)
_REMBG_SESSION = None
_REMBG_SESSION_LOCK = threading.Lock()
# Model preference order: try the high-quality BiRefNet first, fall back to
# isnet, then to u2net (the rembg default). Whichever loads, we keep.
_REMBG_MODEL_CANDIDATES = ("u2net", "isnet-general-use", "birefnet-general")


def _get_rembg_session():
    global _REMBG_SESSION
    if _REMBG_SESSION is not None:
        return _REMBG_SESSION
    try:
        from rembg import new_session
    except Exception:
        return None
    with _REMBG_SESSION_LOCK:
        if _REMBG_SESSION is not None:
            return _REMBG_SESSION
        for name in _REMBG_MODEL_CANDIDATES:
            try:
                _REMBG_SESSION = new_session(name)
                print(f"[rmbg_engine] rembg session: model='{name}'")
                return _REMBG_SESSION
            except Exception as exc:  # noqa: BLE001
                print(f"[rmbg_engine] rembg model '{name}' unavailable ({exc})")
        return None


def _alpha_from_rembg(pil_rgb: Image.Image) -> Optional[np.ndarray]:
    try:
        from rembg import remove
    except Exception:
        return None
    sess = _get_rembg_session()
    try:
        if sess is not None:
            rgba = remove(pil_rgb.convert("RGBA"), session=sess)
        else:
            rgba = remove(pil_rgb.convert("RGBA"))
        arr = np.asarray(rgba.convert("RGBA"), dtype=np.uint8)
        return arr[:, :, 3].astype(np.float32) / 255.0
    except Exception:
        return None


def foreground_rgb_mask(
    image_path: str, mask_thresh: float = 0.5, min_coverage: float = 0.08
) -> Tuple[np.ndarray, np.ndarray, str]:
    """Return (rgb in 0..1, bool mask, mode)."""
    pil = Image.open(image_path).convert("RGB")
    rgb = np.asarray(pil, dtype=np.float32) / 255.0

    alpha = _alpha_from_rmbg(pil)
    mode = "rmbg2"
    if alpha is None or float((alpha > 0.5).mean()) < min_coverage:
        alpha2 = _alpha_from_rembg(pil)
        if alpha2 is not None and float((alpha2 > 0.5).mean()) >= min_coverage:
            alpha = alpha2
            mode = "rembg"

    if alpha is None:
        # Last-resort: simple border-distance segmentation
        h, w = rgb.shape[:2]
        border = np.concatenate(
            [
                rgb[: max(4, h // 20), :, :].reshape(-1, 3),
                rgb[-max(4, h // 20) :, :, :].reshape(-1, 3),
                rgb[:, : max(4, w // 20), :].reshape(-1, 3),
                rgb[:, -max(4, w // 20) :, :].reshape(-1, 3),
            ],
            axis=0,
        )
        bg = np.median(border, axis=0)
        dist = np.sqrt(np.sum((rgb - bg) ** 2, axis=2))
        thr = float(np.percentile(dist, 68))
        mask = dist > max(0.06, thr)
        return rgb, mask, "border_fallback"

    mask = alpha > mask_thresh
    return rgb, mask, mode


def remove_background_to_rgba(image_path: str) -> Image.Image:
    """Return an RGBA PIL image with background alpha-cut, using RMBG-2.0 if available."""
    pil = Image.open(image_path).convert("RGB")
    alpha = _alpha_from_rmbg(pil)
    if alpha is None:
        alpha = _alpha_from_rembg(pil)
    if alpha is None:
        # No segmenter available
        rgba = pil.convert("RGBA")
        return rgba

    arr = np.dstack(
        [np.asarray(pil, dtype=np.uint8), (np.clip(alpha, 0.0, 1.0) * 255).astype(np.uint8)]
    )
    return Image.fromarray(arr, mode="RGBA")
