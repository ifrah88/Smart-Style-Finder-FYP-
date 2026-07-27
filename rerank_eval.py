"""
Evaluate color-aware re-ranking vs pure CLIP, sweeping the blend weight alpha.
Uses the precomputed clip_db + color_feats (dataset items as queries), so it is
fast and needs no model. Regenerates contact sheets at a chosen alpha.
"""
from __future__ import annotations

import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from clip_retrieval import ClipRetrieval

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(BASE_DIR, "eval_out")


def color_at5(eng, alpha, sample=400, seed=42):
    rng = np.random.default_rng(seed)
    N = len(eng.E)
    idxs = rng.choice(N, size=min(sample, N), replace=False)
    hits = 0.0
    for qi in idxs:
        res = eng.search_by_clip_lab(eng.E[qi], eng.lab[qi], k=5, alpha=alpha, exclude_idx=int(qi))
        qcolor = str(eng.meta["colour"][qi])
        hits += sum(1 for r in res if r["colour"] == qcolor) / len(res)
    return hits / len(idxs)


def _font(s=15):
    try:
        return ImageFont.truetype("DejaVuSans.ttf", s)
    except Exception:
        return ImageFont.load_default()


def thumb(path, size=200):
    try:
        im = Image.open(path).convert("RGB")
    except Exception:
        im = Image.new("RGB", (size, size), (60, 60, 60))
    im.thumbnail((size, size))
    c = Image.new("RGB", (size, size), (245, 245, 245))
    c.paste(im, ((size - im.width) // 2, (size - im.height) // 2))
    return c


def sheet(eng, qi, alpha, out, size=200):
    res = eng.search_by_clip_lab(eng.E[qi], eng.lab[qi], k=5, alpha=alpha, exclude_idx=int(qi))
    qcolor = str(eng.meta["colour"][qi])
    cols = 6
    pad, lh = 10, 46
    W = cols * size + (cols + 1) * pad
    H = size + lh + 2 * pad
    s = Image.new("RGB", (W, H), (255, 255, 255))
    dr = ImageDraw.Draw(s)
    f = _font()

    def cell(i, img, lines, accent):
        x = pad + i * (size + pad)
        s.paste(img, (x, pad))
        dr.rectangle([x, pad, x + size, pad + size], outline=accent, width=3)
        for j, ln in enumerate(lines):
            dr.text((x + 2, pad + size + 2 + j * 15), ln[:30], fill=(0, 0, 0), font=f)

    cell(0, thumb(str(eng.meta["image_path"][qi])),
         ["QUERY", f"{qcolor} | {eng.meta['title'][qi][:14]}"], (200, 0, 0))
    for i, r in enumerate(res):
        ok = r["colour"] == qcolor
        cell(i + 1, thumb(r["image_path"]),
             [f"#{i+1} dE={r['deltaE']:.0f}", r["colour"], r["title"][:18]],
             (0, 150, 0) if ok else (170, 120, 0))
    s.save(out)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    eng = ClipRetrieval()
    print(f"DB: {len(eng.E)} products\n")
    print("color-consistency@5 vs alpha (0=pure CLIP style, 1=color only):")
    best_a, best_v = 0.0, -1
    for a in [0.0, 0.2, 0.35, 0.5, 0.65, 0.8]:
        v = color_at5(eng, a)
        flag = ""
        if v > best_v:
            best_v, best_a = v, a
        print(f"  alpha={a:.2f}  ->  {v:.3f}")
    print(f"\nBest: alpha={best_a:.2f} -> color@5={best_v:.3f}  (pure CLIP was alpha=0.00)")

    print(f"\nRegenerating contact sheets at alpha={best_a:.2f} -> eval_out/rr_*.png")
    rng = np.random.default_rng(7)
    for n in range(8):
        qi = int(rng.integers(0, len(eng.E)))
        sheet(eng, qi, best_a, os.path.join(OUT_DIR, f"rr_{n}_{eng.meta['product_ids'][qi]}.png"))
    print("Done.")


if __name__ == "__main__":
    main()
