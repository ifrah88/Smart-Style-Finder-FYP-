"""
Build a small, self-contained bundle for training the CNN on Google Colab (GPU).

The full images_seg/ is ~5.4 GB (originals up to 2000x2400). Training resizes
to 224, so we ship 256px RGBA PNGs instead -> a fraction of the size, no loss
for training. Output: colab_bundle/ and colab_bundle.zip
"""
from __future__ import annotations

import os
import shutil

import pandas as pd
from PIL import Image

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "colab_bundle")
OUT_SEG = os.path.join(OUT, "images_seg")
SIZE = 256


def main():
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT_SEG, exist_ok=True)

    df = pd.read_csv(os.path.join(BASE, "training_data.csv"))
    rows = []
    n_ok = 0
    for _, r in df.iterrows():
        src = str(r["seg_path"])
        if not os.path.isabs(src):
            src = os.path.join(BASE, src)
        if not os.path.exists(src):
            continue
        name = os.path.basename(src)
        try:
            im = Image.open(src).convert("RGBA").resize((SIZE, SIZE), Image.Resampling.BILINEAR)
            im.save(os.path.join(OUT_SEG, name), format="PNG", optimize=True)
        except Exception as e:
            print(f"[skip] {name}: {e}")
            continue
        rr = dict(r)
        rr["seg_path"] = f"images_seg/{name}"   # relative for Colab
        rr["image_path"] = ""                     # raw images not shipped
        rows.append(rr)
        n_ok += 1
        if n_ok % 400 == 0:
            print(f"  resized {n_ok}")

    out_df = pd.DataFrame(rows)
    out_df.to_csv(os.path.join(OUT, "training_data.csv"), index=False)
    shutil.copy(os.path.join(BASE, "train_cnn.py"), os.path.join(OUT, "train_cnn.py"))

    # zip it
    shutil.make_archive(os.path.join(BASE, "colab_bundle"), "zip", OUT)
    size_mb = os.path.getsize(os.path.join(BASE, "colab_bundle.zip")) / 1e6
    print(f"\nBundle: {n_ok} images -> {OUT}")
    print(f"colab_bundle.zip = {size_mb:.0f} MB")


if __name__ == "__main__":
    main()
