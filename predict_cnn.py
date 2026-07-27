"""
Run the trained CNN on one or more images and print the predictions.

Usage:
    python predict_cnn.py path/to/image1.jpg path/to/image2.jpg ...

If no paths are given, picks 8 random images from ./images and runs them.
The RMBG-2.0 segmentation used in training is applied here too so the
input distribution matches what the model saw.
"""

from __future__ import annotations

import os
import pickle
import random
import sys

import numpy as np
import tensorflow as tf
from PIL import Image

from rmbg_engine import foreground_rgb_mask


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "artifacts", "dress_multitask_tf.keras")
ENC_PATH = os.path.join(BASE_DIR, "artifacts", "encoders_tf.pkl")
IMG_SIZE = 224

VALID_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def preprocess(image_path: str) -> np.ndarray:
    rgb, mask, _ = foreground_rgb_mask(image_path)
    # composite onto neutral gray, same as training validation pipeline
    bg = np.full_like(rgb, 0.5, dtype=np.float32)
    a = mask.astype(np.float32)[..., None]
    composed = rgb * a + bg * (1.0 - a)

    pil = Image.fromarray((composed * 255.0).astype(np.uint8), mode="RGB").resize(
        (IMG_SIZE, IMG_SIZE), Image.Resampling.BILINEAR
    )
    return np.asarray(pil, dtype=np.float32) / 255.0


def pick_sample() -> list[str]:
    images_dir = os.path.join(BASE_DIR, "images")
    if not os.path.isdir(images_dir):
        return []
    files = [
        os.path.join(images_dir, f)
        for f in os.listdir(images_dir)
        if os.path.splitext(f)[1].lower() in VALID_EXTS
    ]
    random.seed(0)
    random.shuffle(files)
    return files[:8]


def main() -> None:
    if not os.path.exists(MODEL_PATH) or not os.path.exists(ENC_PATH):
        raise SystemExit(
            "Trained model not found. Run prepare_training_data.py + train_cnn.py first."
        )

    paths = sys.argv[1:] or pick_sample()
    if not paths:
        raise SystemExit("No images supplied and ./images is empty.")

    model = tf.keras.models.load_model(MODEL_PATH, compile=False)
    with open(ENC_PATH, "rb") as f:
        enc = pickle.load(f)
    color_enc = enc["color"]
    design_enc = enc["design"]

    print(f"Running on {len(paths)} image(s)...\n")
    for p in paths:
        try:
            x = preprocess(p)
        except Exception as exc:  # noqa: BLE001
            print(f"[{os.path.basename(p)}]  preprocess ERROR: {exc}")
            continue
        batch = np.expand_dims(x, axis=0)
        pc, pd_ = model.predict(batch, verbose=0)
        ci = int(np.argmax(pc[0]))
        di = int(np.argmax(pd_[0]))
        cc = float(pc[0][ci])
        dc = float(pd_[0][di])
        color = str(color_enc.inverse_transform([ci])[0])
        design = str(design_enc.inverse_transform([di])[0])
        # top-3 colors for diagnostics
        order = np.argsort(pc[0])[::-1][:3]
        top3 = ", ".join(
            f"{str(color_enc.inverse_transform([int(i)])[0])}({float(pc[0][int(i)]):.2f})"
            for i in order
        )
        print(
            f"[{os.path.basename(p)}]  color={color}({cc:.2f})  design={design}({dc:.2f})"
        )
        print(f"   top-3 colors: {top3}")


if __name__ == "__main__":
    main()
