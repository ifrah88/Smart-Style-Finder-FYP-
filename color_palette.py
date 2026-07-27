"""
Dominant-colour palette extraction for garments.

A single mean CIELAB colour is wrong for any multi-colour or printed garment
(red + white print averages to a muddy pink-grey that matches neither). Instead
we describe each garment by up to THREE dominant colours, extracted from the
actual garment pixels of a segmented RGBA PNG:

    pixels (alpha-masked) -> Lab -> k-means (k=3)
      -> merge near-duplicate clusters (deltaE < MERGE_DELTAE)
      -> drop tiny clusters (weight < MIN_WEIGHT)
      -> sort by weight, name each via the nearest colour anchor

This same function is used both to tag every database product (offline) and to
read the colour of a user's query photo (online), so query and database speak
the same language.

Public API:
    pal = extract_palette(seg_path)        # -> Palette
    pal.labs      (M,3) float32   dominant Lab colours, M in 1..3, weight-sorted
    pal.weights   (M,)  float32   pixel fraction of each colour (sums to ~1)
    pal.names     list[str]       nearest anchor colour name per colour
    palette_distance(q, c)         # directional weighted deltaE, query -> candidate
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

import numpy as np
from PIL import Image
from skimage.color import rgb2lab

MAX_COLORS = 3
KMEANS_K = 4          # over-cluster, then merge/prune down to <= MAX_COLORS
MERGE_DELTAE = 12.0   # clusters closer than this are the same colour -> merge
MIN_WEIGHT = 0.08     # drop colours covering < 8% of the garment (shadow/noise)
SKIN_MAX_WEIGHT = 0.25  # a skin-toned cluster below this is model skin -> drop
KMEANS_ITERS = 20

# Colour anchors as (representative RGB, canonical CSV label). Multiple anchors
# can share a base label so that pastels/shades name correctly: a baby-blue
# garment is low-chroma and would otherwise land nearest to white, so we add a
# 'sky blue' anchor that maps back to base 'blue'. The 16 base labels are
# exactly the colour vocabulary of the dataset CSV.
_ANCHORS = {
    "black": ((20, 20, 20), "black"),
    "charcoal": ((55, 55, 60), "black"),
    "white": ((245, 245, 245), "white"),
    "off white": ((238, 233, 222), "white"),
    "cream": ((240, 232, 205), "white"),
    "grey": ((128, 128, 128), "grey"),
    "light grey": ((190, 190, 192), "grey"),
    "blue": ((56, 92, 190), "blue"),
    "navy": ((35, 45, 90), "blue"),
    "sky blue": ((175, 205, 230), "blue"),
    "powder blue": ((205, 222, 235), "blue"),
    "teal": ((33, 140, 150), "green"),
    "turquoise": ((64, 200, 195), "blue"),
    "green": ((58, 152, 77), "green"),
    "mint": ((196, 222, 200), "green"),
    "olive": ((124, 128, 70), "green"),
    "red": ((185, 48, 52), "red"),
    "maroon": ((120, 35, 45), "maroon"),
    "pink": ((225, 105, 150), "pink"),
    "blush": ((235, 200, 205), "pink"),
    "hot pink": ((215, 70, 130), "pink"),
    "fuchsia": ((200, 60, 120), "pink"),
    "rose": ((200, 110, 120), "pink"),
    "purple": ((130, 88, 170), "purple"),
    "lilac": ((190, 165, 210), "lilac"),
    "lavender": ((200, 185, 225), "lilac"),
    "orange": ((220, 130, 35), "orange"),
    "yellow": ((220, 195, 60), "yellow"),
    "lemon": ((235, 225, 140), "yellow"),
    "gold": ((200, 165, 70), "yellow"),
    "mustard": ((183, 149, 43), "yellow"),
    "brown": ((120, 85, 55), "brown"),
    "tan": ((190, 160, 120), "beige"),
    "beige": ((214, 192, 156), "beige"),
    "peach": ((235, 175, 145), "peach"),
    "rust": ((164, 80, 44), "rust"),
}
_ANCHOR_NAMES = list(_ANCHORS.keys())
_ANCHOR_BASE = [_ANCHORS[n][1] for n in _ANCHOR_NAMES]
_ANCHOR_LAB = rgb2lab(
    np.array([_ANCHORS[n][0] for n in _ANCHOR_NAMES], dtype=np.float32)[None, :, :] / 255.0
)[0]


@dataclass
class Palette:
    labs: np.ndarray      # (M,3) float32, weight-sorted
    weights: np.ndarray   # (M,)  float32, sums to ~1
    names: List[str]

    @property
    def dominant_name(self) -> str:
        return self.names[0] if self.names else ""


def _is_skin_lab(lab: np.ndarray) -> bool:
    """Is a Lab centroid in the typical (warm, mid-light) skin-tone box?

    Used to drop the model's face/hands/feet -- but only applied to MINORITY
    clusters, so a genuinely beige/peach/tan garment (a dominant cluster) is
    kept. Per-pixel skin removal was abandoned because it ate tan/gold/peach
    garment pixels."""
    L, a, b = float(lab[0]), float(lab[1]), float(lab[2])
    return (45.0 <= L <= 83.0) and (8.0 <= a <= 24.0) and (13.0 <= b <= 33.0)


def _garment_pixels(seg_path: str, size: int = 128) -> np.ndarray:
    """Lab pixels of the garment (alpha-masked) region of a seg RGBA PNG."""
    pil = Image.open(seg_path).convert("RGBA").resize((size, size), Image.Resampling.BILINEAR)
    arr = np.asarray(pil, dtype=np.float32) / 255.0
    rgb, a = arr[..., :3], arr[..., 3]
    mask = a > 0.5
    if mask.sum() < 50:
        mask = a > 0.2
    if mask.sum() < 10:
        return np.zeros((0, 3), dtype=np.float32)
    return rgb2lab(rgb)[mask].astype(np.float32)


def _kmeans(px: np.ndarray, k: int, iters: int = KMEANS_ITERS):
    """Tiny deterministic Lab k-means. Returns (centers[k,3], weights[k])."""
    n = len(px)
    k = min(k, n)
    rng = np.random.default_rng(42)
    centers = px[rng.choice(n, size=k, replace=False)].copy()
    assign = np.zeros(n, dtype=np.int64)
    for _ in range(iters):
        d = np.sum((px[:, None, :] - centers[None, :, :]) ** 2, axis=2)
        new_assign = np.argmin(d, axis=1)
        if np.array_equal(new_assign, assign):
            break
        assign = new_assign
        for i in range(k):
            m = assign == i
            if m.any():
                centers[i] = px[m].mean(axis=0)
    weights = np.array([(assign == i).mean() for i in range(k)], dtype=np.float32)
    return centers, weights


def _merge_close(centers: np.ndarray, weights: np.ndarray):
    """Merge clusters whose centroids are within MERGE_DELTAE (weighted mean)."""
    order = np.argsort(-weights)
    centers, weights = centers[order], weights[order]
    kept_c: list[np.ndarray] = []
    kept_w: list[float] = []
    for c, w in zip(centers, weights):
        merged = False
        for j, kc in enumerate(kept_c):
            if np.linalg.norm(kc - c) < MERGE_DELTAE:
                tot = kept_w[j] + w
                kept_c[j] = (kc * kept_w[j] + c * w) / max(tot, 1e-9)
                kept_w[j] = tot
                merged = True
                break
        if not merged:
            kept_c.append(c.astype(np.float32))
            kept_w.append(float(w))
    return np.array(kept_c, dtype=np.float32), np.array(kept_w, dtype=np.float32)


_NEUTRAL = {"grey", "beige", "white"}


def name_lab(lab: np.ndarray) -> str:
    """Nearest colour-anchor base label (one of the 16 CSV colours).

    Plain nearest-anchor lets lightness dominate, so low-chroma cool garments
    (pale green, dusty blue/purple) collapse into a neutral (grey/beige/white).
    When the nearest anchor is neutral but the colour clearly points in a cool
    chroma direction (a* < 0 green, b* < 0 blue/purple), we re-pick among the
    chromatic anchors. Saturated colours are unaffected."""
    d = np.linalg.norm(_ANCHOR_LAB - lab[None, :], axis=1)
    base = _ANCHOR_BASE[int(np.argmin(d))]

    L, a, b = float(lab[0]), float(lab[1]), float(lab[2])
    cool = (a < -4.0) or (b < -5.0)
    if base in _NEUTRAL and cool:
        # restrict to chromatic anchors and take the nearest of those
        chrom = np.array([bb not in _NEUTRAL and bb != "black" for bb in _ANCHOR_BASE])
        dc = np.where(chrom, d, np.inf)
        return _ANCHOR_BASE[int(np.argmin(dc))]
    return base


# Canonical base label -> representative Lab (the same-named anchor), used to
# turn colour words in a text query into a target palette.
BASE_LAB = {
    base: _ANCHOR_LAB[_ANCHOR_NAMES.index(base)]
    for base in set(_ANCHOR_BASE)
    if base in _ANCHOR_NAMES
}


def name_to_lab(name: str):
    """Representative Lab for a base colour name, or None if unknown."""
    return BASE_LAB.get(name)


def palette_from_pixels(px: np.ndarray) -> Palette:
    if len(px) == 0:
        return Palette(np.array([[50.0, 0.0, 0.0]], np.float32), np.array([1.0], np.float32), ["grey"])
    centers, weights = _kmeans(px, KMEANS_K)
    centers, weights = _merge_close(centers, weights)

    # Drop minority skin-toned clusters (model face/hands/feet), but never drop
    # everything: a dominant skin-toned cluster is a beige/peach garment.
    skin = np.array([_is_skin_lab(c) for c in centers])
    drop = skin & (weights < SKIN_MAX_WEIGHT)
    if drop.all():
        drop[np.argmax(weights)] = False
    centers, weights = centers[~drop], weights[~drop]

    # prune tiny clusters but always keep at least the dominant one
    keep = weights >= MIN_WEIGHT
    if not keep.any():
        keep[np.argmax(weights)] = True
    centers, weights = centers[keep], weights[keep]

    order = np.argsort(-weights)
    centers, weights = centers[order][:MAX_COLORS], weights[order][:MAX_COLORS]
    weights = weights / weights.sum()
    names = [name_lab(c) for c in centers]
    return Palette(centers, weights, names)


def extract_palette(seg_path: str) -> Palette:
    return palette_from_pixels(_garment_pixels(seg_path))


def palette_distance(q: Palette, c: Palette) -> float:
    """Weighted directional palette distance: every query colour should be
    represented by some candidate colour. Lower = better colour match.

        D = sum_q  w_q * min_c deltaE(q, c)

    Directional (query -> candidate) so that searching for a 'red & white'
    query rewards candidates that contain both, without penalising a candidate
    for extra colours the query never asked about.
    """
    if len(q.labs) == 0 or len(c.labs) == 0:
        return 100.0
    dmat = np.linalg.norm(q.labs[:, None, :] - c.labs[None, :, :], axis=2)  # (Q,C)
    nearest = dmat.min(axis=1)  # best candidate colour per query colour
    return float(np.sum(q.weights * nearest))
