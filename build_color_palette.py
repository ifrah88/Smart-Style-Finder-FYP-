"""
Build the dominant-colour palette artifact for every product, aligned 1:1 with
artifacts/clip_db.npz.

Each product is tagged with up to 3 dominant garment colours (see color_palette).
This replaces the single mean-Lab descriptor (artifacts/color_feats.npz) used by
the retrieval engine, so that multi-colour and printed garments match correctly.

Output: artifacts/color_palette.npz
    labs       (N, 3, 3) float32   up to 3 Lab colours, zero-padded
    weights    (N, 3)    float32   pixel fraction per colour, zero-padded
    counts     (N,)      int32     how many colours are valid (1..3)
    names      (N, 3)    <U10      colour name per slot ('' when padded)
    product_ids(N,)
"""
from __future__ import annotations

import os
import time

import numpy as np

from color_palette import MAX_COLORS, extract_palette

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE_DIR, "artifacts", "clip_db.npz")
OUT = os.path.join(BASE_DIR, "artifacts", "color_palette.npz")


def main() -> None:
    d = np.load(DB, allow_pickle=True)
    seg_paths = d["seg_path"].astype(str)
    n = len(seg_paths)

    labs = np.zeros((n, MAX_COLORS, 3), dtype=np.float32)
    weights = np.zeros((n, MAX_COLORS), dtype=np.float32)
    counts = np.zeros(n, dtype=np.int32)
    names = np.full((n, MAX_COLORS), "", dtype="<U10")

    t0 = time.time()
    for i, p in enumerate(seg_paths):
        try:
            rp = p if os.path.isabs(str(p)) else os.path.join(BASE_DIR, str(p))
            pal = extract_palette(rp)
            m = len(pal.labs)
            labs[i, :m] = pal.labs
            weights[i, :m] = pal.weights
            counts[i] = m
            names[i, :m] = pal.names
        except Exception as exc:  # noqa: BLE001
            print(f"  [warn] palette failed for {p}: {exc}")
            labs[i, 0] = [50.0, 0.0, 0.0]
            weights[i, 0] = 1.0
            counts[i] = 1
            names[i, 0] = "grey"
        if (i + 1) % 400 == 0:
            rate = (i + 1) / (time.time() - t0)
            print(f"  {i+1}/{n}  ({rate:.0f}/s)")

    np.savez_compressed(
        OUT, labs=labs, weights=weights, counts=counts,
        names=names, product_ids=d["product_ids"],
    )
    print(f"Saved palettes {labs.shape} -> {OUT}")


if __name__ == "__main__":
    main()
