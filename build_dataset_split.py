"""
Create an explicit, reproducible train/test split of the labelled data and lay
it out as folders of images (raw + segmented) plus CSV manifests.

The split EXACTLY matches the one train_cnn.py uses internally
(test_size=0.15, stratified on design, random_state=42), so dataset/test.csv is
the held-out set behind the reported accuracy (colour 58.2% / design 69.7%).

Layout produced:
    dataset/
      train.csv, test.csv          product_id, colour, design, title, price,
                                    fabric, brand, image_path, seg_path
      train/images/  train/images_seg/
      test/images/   test/images_seg/
      README.md
"""
from __future__ import annotations

import os
import shutil

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

BASE = os.path.dirname(os.path.abspath(__file__))
CSV = os.path.join(BASE, "training_data.csv")
OUT = os.path.join(BASE, "dataset")
SEED, TEST_SIZE = 42, 0.15


def _abs(p):
    return p if os.path.isabs(str(p)) else os.path.join(BASE, str(p))


def main():
    df = pd.read_csv(CSV)
    # same filtering as train_cnn: keep rows whose segmented image exists
    df = df[df["seg_path"].astype(bool)].reset_index(drop=True)
    df = df[df["seg_path"].apply(lambda p: os.path.exists(_abs(p)))].reset_index(drop=True)

    yd = LabelEncoder().fit_transform(df["design"].values)  # stratify target
    idx = np.arange(len(df))
    train_idx, test_idx = train_test_split(
        idx, test_size=TEST_SIZE, random_state=SEED, stratify=yd
    )
    print(f"rows={len(df)}  train={len(train_idx)}  test={len(test_idx)}")

    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    for split in ("train", "test"):
        for sub in ("images", "images_seg"):
            os.makedirs(os.path.join(OUT, split, sub), exist_ok=True)

    cols = ["product_id", "colour", "design", "title", "price", "fabric", "brand"]

    def build(split, indices):
        rows = []
        for i in indices:
            r = df.iloc[i]
            pid = str(r["product_id"])
            rec = {c: r.get(c, "") for c in cols}
            # copy raw image (if present)
            new_img = ""
            src_img = _abs(r.get("image_path", ""))
            if r.get("image_path", "") and os.path.exists(src_img):
                name = os.path.basename(src_img)
                shutil.copy(src_img, os.path.join(OUT, split, "images", name))
                new_img = f"dataset/{split}/images/{name}"
            # copy segmented image
            src_seg = _abs(r["seg_path"])
            seg_name = os.path.basename(src_seg)
            shutil.copy(src_seg, os.path.join(OUT, split, "images_seg", seg_name))
            rec["image_path"] = new_img
            rec["seg_path"] = f"dataset/{split}/images_seg/{seg_name}"
            rows.append(rec)
        out_df = pd.DataFrame(rows, columns=cols + ["image_path", "seg_path"])
        out_df.to_csv(os.path.join(OUT, f"{split}.csv"), index=False)
        return out_df

    tr = build("train", train_idx)
    te = build("test", test_idx)
    print(f"wrote dataset/train.csv ({len(tr)}) and dataset/test.csv ({len(te)})")

    # split-distribution summary for the README
    def dist(d, col):
        return d[col].value_counts().to_dict()

    readme = f"""# Dataset — train / test split

Reproducible split of the {len(df)} labelled products used to train and evaluate
the multi-task CNN (colour + design). Created by `build_dataset_split.py`.

- **Method:** stratified on `design`, `test_size={TEST_SIZE}`, `random_state={SEED}`
- **This is the exact split `train_cnn.py` uses**, so `test.csv` is the held-out
  evaluation set behind the reported accuracy (colour 58.2% / design 69.7%).

| Split | Products |
|---|---|
| train | {len(tr)} |
| test  | {len(te)} |

Each split folder contains `images/` (raw) and `images_seg/` (background-removed).
The CSVs list `product_id, colour, design, title, price, fabric, brand` plus the
relative `image_path` and `seg_path`.

Train design distribution: {dist(tr,'design')}
Test  design distribution: {dist(te,'design')}
Train colour distribution: {dist(tr,'colour')}
Test  colour distribution: {dist(te,'colour')}
"""
    with open(os.path.join(OUT, "README.md"), "w") as f:
        f.write(readme)
    print("wrote dataset/README.md")


if __name__ == "__main__":
    main()
