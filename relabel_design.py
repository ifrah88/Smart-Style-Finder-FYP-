"""
Build clean, learnable 'design' labels to replace the fake heuristic ones.

Label sources, in priority order:
    1. Product TITLE keywords -- these are REAL merchant labels from Sapphire
       ("Embroidered ...", "Printed Suit", "Solid Lawn ...", "... Jacquard ...",
       "Embellished ...").  ~59% of rows are covered this way.
    2. FashionCLIP zero-shot among ONLY the 5 coarse classes for the remaining
       rows.  CLIP separates 5 coarse, visually-distinct types far more reliably
       than the original 11 fine classes (which collapsed 63% into one bucket).

Coarse taxonomy: printed, embroidered, embellished, jacquard, solid
These are visually distinct and truly distinguishable, so the CNN can actually
learn them (unlike abstract vs geometric vs mixed print).

Reuses precomputed image embeddings in artifacts/clip_db.npz for the fallback.

Outputs:
    training_data.csv                  (design column replaced; backup kept once)
    Adds column: design_source  (title | clip)
"""
from __future__ import annotations

import os
import re
import shutil

import numpy as np
import pandas as pd
import torch
from transformers import CLIPModel, CLIPProcessor

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE_DIR, "artifacts", "clip_db.npz")
CSV = os.path.join(BASE_DIR, "training_data.csv")
BACKUP = os.path.join(BASE_DIR, "training_data.heuristic_design.csv")
MODEL_ID = "patrickjohncyh/fashion-clip"

CLASSES = ["printed", "embroidered", "embellished", "jacquard", "solid"]

COARSE_PROMPTS = {
    "printed": [
        "a garment with a printed pattern",
        "a digital printed dress",
        "clothing covered in a print",
    ],
    "embroidered": [
        "a garment with thread embroidery",
        "an embroidered dress",
        "clothing with embroidered surface",
    ],
    "embellished": [
        "an embellished garment with sequins or beads",
        "a garment decorated with embellishment and adornments",
    ],
    "jacquard": [
        "a tone-on-tone jacquard woven garment",
        "a textured woven dobby fabric with no print",
    ],
    "solid": [
        "a plain solid color garment with no print or embroidery",
        "a plain single color dress",
    ],
}


def title_label(title: str):
    t = str(title).lower()
    if "embroider" in t:
        return "embroidered"
    if "embellish" in t:
        return "embellished"
    if "jacquard" in t or "dobby" in t:
        return "jacquard"
    if "print" in t:
        return "printed"
    if re.search(r"\bsolid\b|\bplain\b", t):
        return "solid"
    return None


def encode_text(model, proc, prompts):
    inp = proc(text=prompts, return_tensors="pt", padding=True, truncation=True)
    with torch.no_grad():
        f = model.get_text_features(**inp)
    f = f / f.norm(p=2, dim=-1, keepdim=True)
    return f.cpu().numpy().astype(np.float32)


def main():
    d = np.load(DB, allow_pickle=True)
    pids = d["product_ids"].astype(str)
    E = d["embeddings"].astype(np.float32)
    emb_by_pid = dict(zip(pids, E))

    df = pd.read_csv(CSV)
    if not os.path.exists(BACKUP):
        shutil.copy(CSV, BACKUP)
        print(f"Backed up old labels -> {BACKUP}")

    # 1) title labels
    designs = []
    sources = []
    need_clip_idx = []
    for i, row in df.iterrows():
        lab = title_label(row.get("title", ""))
        if lab:
            designs.append(lab); sources.append("title")
        else:
            designs.append(None); sources.append("clip")
            need_clip_idx.append(i)

    # 2) CLIP coarse fallback for the rest
    if need_clip_idx:
        model = CLIPModel.from_pretrained(MODEL_ID).eval()
        proc = CLIPProcessor.from_pretrained(MODEL_ID)
        C = np.vstack([
            (lambda v: v / max(np.linalg.norm(v), 1e-8))(
                encode_text(model, proc, COARSE_PROMPTS[c]).mean(axis=0))
            for c in CLASSES
        ]).astype(np.float32)
        for i in need_clip_idx:
            pid = str(df.at[i, "product_id"])
            e = emb_by_pid.get(pid)
            if e is None:
                designs[i] = "printed"  # safe majority fallback
                continue
            designs[i] = CLASSES[int(np.argmax(e @ C.T))]

    df["design"] = designs
    df["design_source"] = sources
    df = df.drop(columns=[c for c in ["design_clip_conf"] if c in df.columns])
    df.to_csv(CSV, index=False)

    print(f"Relabeled {len(df)} rows.")
    print(f"Source: title={sources.count('title')}  clip={sources.count('clip')}")
    print("New design distribution:")
    print(df["design"].value_counts().to_string())


if __name__ == "__main__":
    main()
