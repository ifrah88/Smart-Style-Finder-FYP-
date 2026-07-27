"""
Build a FashionCLIP retrieval database from the already-segmented images.

Why this replaces build_fashion_clip_embeddings.py:
    * Uses the existing RGBA seg PNGs in images_seg/ (background already removed)
      composited onto neutral gray -- no RMBG re-run, no rembg dependency.
    * Reads training_data.csv (local paths, real metadata) instead of the old
      retrieval_index.pkl that still held Windows absolute paths.
    * Batched image encoding for speed on CPU.

Output:
    artifacts/clip_db.npz   (product_ids, embeddings[N,D], and metadata columns)
"""
from __future__ import annotations

import os
import time

import numpy as np
import pandas as pd
from PIL import Image

import torch
from transformers import CLIPModel, CLIPProcessor

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV = os.path.join(BASE_DIR, "training_data.csv")
ART = os.path.join(BASE_DIR, "artifacts")
OUT = os.path.join(ART, "clip_db.npz")
MODEL_ID = "patrickjohncyh/fashion-clip"
IMG_SIZE = 224
BATCH = 16


def load_seg_on_gray(seg_path: str, size: int = IMG_SIZE) -> Image.Image:
    """Load an RGBA seg PNG and composite the garment onto neutral gray."""
    pil = Image.open(seg_path).convert("RGBA").resize((size, size), Image.Resampling.BILINEAR)
    arr = np.asarray(pil, dtype=np.float32) / 255.0
    rgb, a = arr[..., :3], arr[..., 3:4]
    gray = np.full_like(rgb, 0.5)
    out = rgb * a + gray * (1.0 - a)
    return Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8), mode="RGB")


def main() -> None:
    os.makedirs(ART, exist_ok=True)
    df = pd.read_csv(CSV)
    df = df[df["seg_path"].astype(bool)].reset_index(drop=True)
    print(f"Embedding {len(df)} products with {MODEL_ID} ...")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = CLIPModel.from_pretrained(MODEL_ID).to(device).eval()
    processor = CLIPProcessor.from_pretrained(MODEL_ID)

    embs = []
    t0 = time.time()
    paths = [p if os.path.isabs(str(p)) else os.path.join(BASE_DIR, str(p))
             for p in df["seg_path"].tolist()]
    for start in range(0, len(paths), BATCH):
        batch_paths = paths[start : start + BATCH]
        imgs = [load_seg_on_gray(p) for p in batch_paths]
        inputs = processor(images=imgs, return_tensors="pt").to(device)
        with torch.no_grad():
            feats = model.get_image_features(**inputs)
        feats = feats / feats.norm(p=2, dim=-1, keepdim=True)
        embs.append(feats.cpu().numpy().astype(np.float32))
        done = start + len(batch_paths)
        if done % (BATCH * 5) == 0 or done == len(paths):
            rate = done / max(time.time() - t0, 1e-6)
            print(f"  {done}/{len(paths)}  ({rate:.1f} img/s)")

    E = np.vstack(embs).astype(np.float32)
    np.savez_compressed(
        OUT,
        product_ids=df["product_id"].astype(str).values,
        embeddings=E,
        colour=df["colour"].astype(str).values,
        design=df["design"].astype(str).values,
        title=df["title"].astype(str).values,
        price=df["price"].astype(str).values,
        fabric=df["fabric"].astype(str).values,
        brand=df["brand"].astype(str).values,
        image_path=df["image_path"].astype(str).values,
        seg_path=df["seg_path"].astype(str).values,
    )
    print(f"Saved {len(E)} embeddings (dim={E.shape[1]}) -> {OUT}")


if __name__ == "__main__":
    main()
