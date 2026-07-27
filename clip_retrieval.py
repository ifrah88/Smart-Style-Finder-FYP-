"""
Colour-aware FashionCLIP retrieval engine (the search core for the app).

Pipeline:
    1. Shortlist top-M products by CLIP cosine similarity (style / pattern / type).
    2. Re-rank the shortlist by fusing CLIP similarity with an explicit garment
       COLOUR match, since CLIP alone is weak on exact colour.

Colour is represented by up to 3 dominant garment colours per item (a palette),
extracted from the actual garment pixels (see color_palette). This replaces the
old single mean-Lab descriptor, which produced a muddy averaged colour for
multi-colour and printed garments. The query photo is described by the SAME
palette extractor, so query and database speak the same colour language.

    combined = (1 - alpha) * clip_norm + alpha * colour_norm

Both terms are min-max normalized within the shortlist so the blend is stable.
alpha=0 -> pure CLIP (style only); alpha=1 -> colour dominates.

Public API:
    eng = ClipRetrieval()                          # loads DB once
    eng.search_by_seg(seg_path, k=5)               # query a segmented RGBA PNG
    eng.search_by_text("baby pink dress", k=5)     # query a text description
    eng.search_by_palette(clip_emb, labs, weights) # query with precomputed features
"""
from __future__ import annotations

import os
from typing import List, Optional

import numpy as np
from PIL import Image

from color_palette import extract_palette

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE_DIR, "artifacts", "clip_db.npz")
PALETTE = os.path.join(BASE_DIR, "artifacts", "color_palette.npz")
MODEL_ID = "patrickjohncyh/fashion-clip"

SHORTLIST = 200      # candidate pool reranked by colour; also the max results
DEFAULT_ALPHA = 0.7  # blend weight; colour-aware re-rank of the CLIP shortlist
DELTAE_TAU = 22.0    # smaller => stricter colour matching


def _minmax(x: np.ndarray) -> np.ndarray:
    lo, hi = float(x.min()), float(x.max())
    if hi - lo < 1e-9:
        return np.ones_like(x)
    return (x - lo) / (hi - lo)


def _chroma_weight(labs, weights):
    """Re-weight a garment palette toward its vivid (chromatic) colours.

    A busy multi-colour print splits into several near-equal colours (e.g. a teal
    kurta -> teal + dark-motif + neutral). Matching on equal weights then rewards
    dull/neutral candidates and pulls away from the obvious dominant colour. We
    scale each colour's weight by its chroma (distance from grey in Lab), so the
    vivid colour leads. Neutral garments are unaffected (all colours low-chroma,
    so their relative order is preserved)."""
    labs = np.asarray(labs, np.float32).reshape(-1, 3)
    weights = np.asarray(weights, np.float32).reshape(-1)
    chroma = np.sqrt(labs[:, 1] ** 2 + labs[:, 2] ** 2)
    factor = np.maximum(chroma, 3.0) ** 1.5  # floor so all-neutral palettes stay sane
    w = weights * factor
    s = float(w.sum())
    return w / s if s > 1e-9 else weights


def seg_to_clip_input(seg_path: str, size: int = 224) -> Image.Image:
    pil = Image.open(seg_path).convert("RGBA").resize((size, size), Image.Resampling.BILINEAR)
    arr = np.asarray(pil, dtype=np.float32) / 255.0
    rgb, a = arr[..., :3], arr[..., 3:4]
    gray = np.full_like(rgb, 0.5)
    out = rgb * a + gray * (1.0 - a)
    return Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8), mode="RGB")


class ClipRetrieval:
    def __init__(self):
        d = np.load(DB, allow_pickle=True)
        self.E = d["embeddings"].astype(np.float32)
        self.meta = {k: d[k] for k in d.files if k != "embeddings"}
        # Stored image/seg paths are relative (portable); resolve to absolute
        # against this folder so results carry valid paths wherever the app lives.
        for key in ("image_path", "seg_path"):
            if key in self.meta:
                self.meta[key] = np.array([
                    pp if os.path.isabs(pp) else os.path.join(BASE_DIR, pp)
                    for pp in self.meta[key].astype(str)
                ])

        p = np.load(PALETTE, allow_pickle=True)
        self.pal_labs = p["labs"].astype(np.float32)        # (N,3,3)
        self.pal_weights = p["weights"].astype(np.float32)  # (N,3)
        self.pal_counts = p["counts"].astype(np.int32)      # (N,)
        self.pal_names = p["names"].astype(str)             # (N,3)

        self._model = None
        self._proc = None

    # ---- model (lazy) -----------------------------------------------------
    def _ensure_model(self):
        if self._model is None:
            import torch  # noqa
            from transformers import CLIPModel, CLIPProcessor
            self._model = CLIPModel.from_pretrained(MODEL_ID).eval()
            self._proc = CLIPProcessor.from_pretrained(MODEL_ID)

    def clip_embed(self, pil_rgb: Image.Image) -> np.ndarray:
        import torch
        self._ensure_model()
        inp = self._proc(images=pil_rgb, return_tensors="pt")
        with torch.no_grad():
            f = self._model.get_image_features(**inp)
        f = f / f.norm(p=2, dim=-1, keepdim=True)
        return f.cpu().numpy()[0].astype(np.float32)

    def text_embed(self, text: str) -> np.ndarray:
        import torch
        self._ensure_model()
        inp = self._proc(text=[text], return_tensors="pt", padding=True, truncation=True)
        with torch.no_grad():
            f = self._model.get_text_features(**inp)
        f = f / f.norm(p=2, dim=-1, keepdim=True)
        return f.cpu().numpy()[0].astype(np.float32)

    # ---- colour matching --------------------------------------------------
    def _palette_color_dist(self, idxs, q_labs, q_weights) -> np.ndarray:
        """Directional weighted palette distance from the query palette to each
        candidate in idxs:  D = sum_q w_q * min_c deltaE(q_color, cand_color).

        Lower = better colour match. Returns (len(idxs),)."""
        cl = self.pal_labs[idxs]        # (S,3,3)
        cw = self.pal_weights[idxs]     # (S,3)
        valid = cw > 0                  # (S,3)
        # deltaE between each query colour and each candidate colour
        diff = q_labs[None, :, None, :] - cl[:, None, :, :]  # (S,Q,3,3)
        dd = np.linalg.norm(diff, axis=-1)                   # (S,Q,3)
        dd = np.where(valid[:, None, :], dd, np.inf)
        nearest = dd.min(axis=2)                             # (S,Q)
        return (nearest * q_weights[None, :]).sum(axis=1)    # (S,)

    def search_by_palette(self, clip_emb, q_labs, q_weights, k=5,
                          alpha=DEFAULT_ALPHA,
                          exclude_idx: Optional[int] = None) -> List[dict]:
        q_labs = np.asarray(q_labs, dtype=np.float32).reshape(-1, 3)
        q_weights = np.asarray(q_weights, dtype=np.float32).reshape(-1)
        q_weights = q_weights / max(q_weights.sum(), 1e-9)

        sims = self.E @ clip_emb
        order = np.argsort(-sims)
        if exclude_idx is not None:
            order = order[order != exclude_idx]
        shortlist = order[:SHORTLIST]

        clip_s = sims[shortlist]
        color_d = self._palette_color_dist(shortlist, q_labs, q_weights)
        color_s = np.exp(-color_d / DELTAE_TAU)

        combined = (1 - alpha) * _minmax(clip_s) + alpha * _minmax(color_s)
        order_local = np.argsort(-combined)  # all shortlist positions, best first

        out = []
        seen_pids = set()
        for j in order_local:
            idx = int(shortlist[j])
            pid = str(self.meta["product_ids"][idx])
            if pid in seen_pids:  # dataset has duplicate listings -> show each once
                continue
            seen_pids.add(pid)
            cnt = int(self.pal_counts[idx])
            out.append({
                "idx": int(idx),
                "score": float(combined[j]),   # 0..1 relative match (CLIP+colour)
                "clip_sim": float(sims[idx]),
                "color_dist": float(color_d[j]),
                "palette": [str(x) for x in self.pal_names[idx][:cnt]],
                "colour": str(self.meta["colour"][idx]),
                "design": str(self.meta["design"][idx]),
                "brand": str(self.meta["brand"][idx]),
                "fabric": str(self.meta["fabric"][idx]),
                "title": str(self.meta["title"][idx]),
                "price": str(self.meta["price"][idx]),
                "image_path": str(self.meta["image_path"][idx]),
                "product_id": str(self.meta["product_ids"][idx]),
            })
            if len(out) >= k:
                break
        return out

    # back-compat: single-colour query == 1-colour palette
    def search_by_clip_lab(self, clip_emb, lab, k=5, alpha=DEFAULT_ALPHA,
                           exclude_idx: Optional[int] = None) -> List[dict]:
        return self.search_by_palette(clip_emb, np.asarray(lab).reshape(1, 3),
                                      np.array([1.0], np.float32), k=k,
                                      alpha=alpha, exclude_idx=exclude_idx)

    def query_palette(self, idx: int):
        """Stored (labs, weights) palette of a database item -- for evaluation
        where dataset items act as queries."""
        c = int(self.pal_counts[idx])
        return self.pal_labs[idx][:c], self.pal_weights[idx][:c]

    # ---- query entry points ----------------------------------------------
    def search_by_seg(self, seg_path, k=5, alpha=DEFAULT_ALPHA) -> List[dict]:
        emb = self.clip_embed(seg_to_clip_input(seg_path))
        pal = extract_palette(seg_path)
        w = _chroma_weight(pal.labs, pal.weights)
        return self.search_by_palette(emb, pal.labs, w, k=k, alpha=alpha)

    def search_by_image(self, image_path, k=5, alpha=DEFAULT_ALPHA) -> List[dict]:
        """Search from a RAW uploaded photo (no alpha channel).

        Removes the background (RMBG, with a border-heuristic fallback) so the
        garment colour isn't polluted, composites onto neutral gray for CLIP,
        and builds the colour palette from the foreground pixels. If background
        removal is unavailable, falls back to a centre crop of the full image.
        """
        from skimage.color import rgb2lab
        from color_palette import palette_from_pixels

        rgb = mask = None
        # 1) preferred: clothes segmentation -> garment pixels only (no skin/bg)
        try:
            from garment_segmenter import segment_garment
            rgb, m = segment_garment(image_path)  # rgb 0..1, bool mask
            mask = m.astype(np.float32)
        except Exception:
            rgb = mask = None
        # 2) fallback: generic background removal (keeps person)
        if rgb is None:
            try:
                from rmbg_engine import foreground_rgb_mask
                rgb, mask, _ = foreground_rgb_mask(image_path)
            except Exception:
                rgb = mask = None

        if rgb is None:
            # fallback: use a centre crop (garment usually centred in product shots)
            pil = Image.open(image_path).convert("RGB")
            w, h = pil.size
            pil = pil.crop((int(w * 0.12), int(h * 0.05), int(w * 0.88), int(h * 0.95)))
            rgb = np.asarray(pil, np.float32) / 255.0
            mask = np.ones(rgb.shape[:2], np.float32)

        # downscale for speed/consistency
        small = Image.fromarray((np.clip(rgb, 0, 1) * 255).astype(np.uint8)).resize((256, 256))
        small_m = Image.fromarray((mask * 255).astype(np.uint8)).resize((256, 256))
        rgb_s = np.asarray(small, np.float32) / 255.0
        m_s = np.asarray(small_m, np.float32) / 255.0

        # CLIP input: composite garment on neutral gray
        a = m_s[..., None]
        comp = rgb_s * a + 0.5 * (1.0 - a)
        emb = self.clip_embed(Image.fromarray((comp * 255).astype(np.uint8), mode="RGB"))

        # palette from foreground pixels
        sel = m_s > 0.5
        px = rgb2lab(rgb_s)[sel] if sel.sum() > 50 else rgb2lab(rgb_s).reshape(-1, 3)
        pal = palette_from_pixels(px.astype(np.float32))
        w = _chroma_weight(pal.labs, pal.weights)
        return self.search_by_palette(emb, pal.labs, w, k=k, alpha=alpha)

    def _colors_in_text(self, text: str):
        """Lab targets for every known colour word mentioned in the query."""
        from color_palette import BASE_LAB
        t = text.lower()
        labs, names = [], []
        for name in sorted(BASE_LAB, key=lambda s: -len(s)):
            if name in t and name not in names:
                labs.append(BASE_LAB[name])
                names.append(name)
        return (np.array(labs, np.float32), names) if labs else (None, [])

    def search_by_text(self, text: str, k=5, alpha=DEFAULT_ALPHA) -> List[dict]:
        """Text query (SRS: e.g. 'baby pink embroidered dress').

        Ranks by CLIP text->image similarity; if the text names colour(s), the
        result is colour-reranked toward those colours' anchor palette."""
        emb = self.text_embed(text)
        labs, _ = self._colors_in_text(text)
        if labs is None:
            # no colour mentioned -> pure CLIP semantic ranking
            return self.search_by_palette(emb, np.array([[50.0, 0.0, 0.0]], np.float32),
                                          np.array([1.0], np.float32), k=k, alpha=0.0)
        w = np.ones(len(labs), np.float32)
        return self.search_by_palette(emb, labs, w, k=k, alpha=alpha)
