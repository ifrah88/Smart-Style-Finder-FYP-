"""
Train a multi-task CNN (color + design) on your dress dataset.

Backbone:        ResNet50 (ImageNet pretrained, classic CNN)
Input:           224x224 RGB
Heads:           color softmax + design softmax sharing a 256-d embedding
Augmentations:
    * random horizontal flip
    * small rotation (<= 10 deg)
    * random crop (90-100% of frame)
    * random background composition (the dress was pre-segmented, so we
      paste it onto a random solid-colour or randomly-textured canvas every
      step). This is the key piece that teaches the model to ignore the
      background instead of memorising the studio backdrop.
    * mild brightness/contrast jitter
    * NO hue/saturation jitter (would destroy the color label signal)
Training:
    Phase 1  - backbone frozen, train heads only           (10 epochs)
    Phase 2  - unfreeze top 40 layers, lr = 1e-4           ( 8 epochs)
    Phase 3  - unfreeze all,        lr = 1e-5              ( 4 epochs)
Loss:            sparse categorical crossentropy, both heads, class weights
                 computed from the training split
Outputs:
    artifacts/dress_multitask_tf.keras   (loaded by gui.py)
    artifacts/encoders_tf.pkl            (loaded by gui.py)
    artifacts/train_report.txt           (per-class accuracy, confusion summary)

Pre-req:
    Run python prepare_training_data.py once first.

Run:
    python train_cnn.py
    python train_cnn.py --quick   # short verification run (1+1+1 epochs)
"""

from __future__ import annotations

import argparse
import os
import pickle
import random
import time
from typing import Tuple

import numpy as np
import pandas as pd
from PIL import Image
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.utils.class_weight import compute_class_weight

import tensorflow as tf

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TRAIN_CSV = os.path.join(BASE_DIR, "training_data.csv")
ART_DIR = os.path.join(BASE_DIR, "artifacts")
MODEL_PATH = os.path.join(ART_DIR, "dress_multitask_tf.keras")
ENC_PATH = os.path.join(ART_DIR, "encoders_tf.pkl")
REPORT_PATH = os.path.join(ART_DIR, "train_report.txt")

IMG_SIZE = 224
EMBED_DIM = 256
SEED = 42

# Solid-colour background palette used for augmentation. Generic so the model
# can't learn "background = white = studio shot" shortcuts.
BG_COLORS = np.array(
    [
        [255, 255, 255],
        [240, 240, 240],
        [220, 220, 220],
        [200, 200, 200],
        [180, 180, 180],
        [150, 150, 150],
        [120, 120, 120],
        [90, 90, 90],
        [60, 60, 60],
        [30, 30, 30],
        [10, 10, 10],
        [200, 180, 160],
        [160, 180, 200],
        [180, 200, 160],
        [200, 160, 180],
        [220, 200, 180],
        [180, 200, 220],
    ],
    dtype=np.float32,
)


def set_seeds() -> None:
    random.seed(SEED)
    np.random.seed(SEED)
    tf.random.set_seed(SEED)


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


def load_segmented_rgba(path: str, size: int = IMG_SIZE) -> Tuple[np.ndarray, np.ndarray]:
    """Return (rgb [size,size,3] float32 0..1, alpha [size,size] float32 0..1)."""
    pil = Image.open(path).convert("RGBA").resize((size, size), Image.Resampling.BILINEAR)
    arr = np.asarray(pil, dtype=np.float32) / 255.0
    return arr[..., :3], arr[..., 3]


def random_background(size: int) -> np.ndarray:
    """Sample a random background canvas (solid or vertical/horizontal gradient)."""
    r = random.random()
    if r < 0.6:
        # solid
        c = BG_COLORS[random.randrange(len(BG_COLORS))] / 255.0
        bg = np.tile(c, (size, size, 1))
    elif r < 0.85:
        # vertical gradient between two colors
        c1 = BG_COLORS[random.randrange(len(BG_COLORS))] / 255.0
        c2 = BG_COLORS[random.randrange(len(BG_COLORS))] / 255.0
        t = np.linspace(0, 1, size, dtype=np.float32).reshape(-1, 1, 1)
        bg = c1 * (1 - t) + c2 * t
        bg = np.broadcast_to(bg, (size, size, 3)).copy()
    else:
        # smooth noise
        small = np.random.rand(8, 8, 3).astype(np.float32) * 0.4 + 0.3
        bg = np.asarray(
            Image.fromarray((small * 255).astype(np.uint8)).resize((size, size), Image.Resampling.BILINEAR),
            dtype=np.float32,
        ) / 255.0
    return bg.astype(np.float32)


def augment_train(rgb: np.ndarray, alpha: np.ndarray) -> np.ndarray:
    """Apply augmentation pipeline AND composite onto a random background."""
    # Random horizontal flip
    if random.random() < 0.5:
        rgb = np.ascontiguousarray(rgb[:, ::-1, :])
        alpha = np.ascontiguousarray(alpha[:, ::-1])

    # Random rotation (PIL handles RGBA together so dress + mask stay aligned)
    if random.random() < 0.5:
        angle = random.uniform(-10, 10)
        pil = Image.fromarray(
            np.dstack(
                [
                    (rgb * 255).astype(np.uint8),
                    (alpha * 255).astype(np.uint8),
                ]
            ),
            mode="RGBA",
        ).rotate(angle, resample=Image.BILINEAR, expand=False)
        arr = np.asarray(pil, dtype=np.float32) / 255.0
        rgb = arr[..., :3]
        alpha = arr[..., 3]

    # Random crop 90-100% then resize back
    if random.random() < 0.5:
        h, w = rgb.shape[:2]
        scale = random.uniform(0.88, 1.0)
        ch = int(h * scale)
        cw = int(w * scale)
        y0 = random.randint(0, h - ch)
        x0 = random.randint(0, w - cw)
        rgb = rgb[y0 : y0 + ch, x0 : x0 + cw, :]
        alpha = alpha[y0 : y0 + ch, x0 : x0 + cw]
        rgb = np.asarray(
            Image.fromarray((rgb * 255).astype(np.uint8)).resize((w, h), Image.Resampling.BILINEAR),
            dtype=np.float32,
        ) / 255.0
        alpha = np.asarray(
            Image.fromarray((alpha * 255).astype(np.uint8)).resize((w, h), Image.Resampling.BILINEAR),
            dtype=np.float32,
        ) / 255.0

    # Brightness / contrast jitter (mild, no hue)
    if random.random() < 0.5:
        b = random.uniform(-0.08, 0.08)
        c = random.uniform(0.92, 1.08)
        rgb = np.clip((rgb - 0.5) * c + 0.5 + b, 0.0, 1.0)

    # Background composite
    bg = random_background(rgb.shape[0])
    a = alpha[..., None]
    composed = rgb * a + bg * (1.0 - a)
    return composed.astype(np.float32)


def composite_val(rgb: np.ndarray, alpha: np.ndarray) -> np.ndarray:
    """Validation/inference compositing onto a fixed neutral gray."""
    bg = np.full_like(rgb, 0.5, dtype=np.float32)
    a = alpha[..., None]
    return (rgb * a + bg * (1.0 - a)).astype(np.float32)


# ---------------------------------------------------------------------------
# tf.data pipeline
# ---------------------------------------------------------------------------


def make_dataset(
    seg_paths: np.ndarray,
    yc: np.ndarray,
    yd: np.ndarray,
    batch_size: int,
    training: bool,
) -> tf.data.Dataset:
    """Yield (x, y_dict). Class balancing is handled inside the loss function."""

    def gen():
        idxs = np.arange(len(seg_paths))
        if training:
            np.random.shuffle(idxs)
        for i in idxs:
            try:
                rgb, alpha = load_segmented_rgba(seg_paths[i])
            except Exception:
                continue
            if training:
                x = augment_train(rgb, alpha)
            else:
                x = composite_val(rgb, alpha)
            yield x, {"color": int(yc[i]), "design": int(yd[i])}

    out_sig = (
        tf.TensorSpec(shape=(IMG_SIZE, IMG_SIZE, 3), dtype=tf.float32),
        {
            "color": tf.TensorSpec(shape=(), dtype=tf.int32),
            "design": tf.TensorSpec(shape=(), dtype=tf.int32),
        },
    )
    ds = tf.data.Dataset.from_generator(gen, output_signature=out_sig)
    ds = ds.batch(batch_size).prefetch(tf.data.AUTOTUNE)
    return ds


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------


def build_model(num_colors: int, num_designs: int) -> Tuple[tf.keras.Model, tf.keras.Model]:
    base = tf.keras.applications.ResNet50(
        include_top=False, input_shape=(IMG_SIZE, IMG_SIZE, 3), weights="imagenet"
    )
    base.trainable = False

    inp = tf.keras.Input(shape=(IMG_SIZE, IMG_SIZE, 3))
    # ResNet50 expects 0-255 RGB, then its preprocess_input does
    # caffe-style mean subtraction (BGR conversion + mean offsets).
    x = inp * 255.0
    x = tf.keras.applications.resnet.preprocess_input(x)
    x = base(x, training=False)
    x = tf.keras.layers.GlobalAveragePooling2D()(x)
    x = tf.keras.layers.Dropout(0.35)(x)
    emb = tf.keras.layers.Dense(EMBED_DIM, activation="relu", name="embedding")(x)
    color_out = tf.keras.layers.Dense(num_colors, activation="softmax", name="color")(emb)
    design_out = tf.keras.layers.Dense(num_designs, activation="softmax", name="design")(emb)

    model = tf.keras.Model(inp, [color_out, design_out])
    return model, base


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------


def compute_weights(y: np.ndarray, cap: float = 3.0) -> dict[int, float]:
    """Sqrt-damped, capped class weights.

    Plain 'balanced' weights (N / (K*count)) over-amplify tiny classes: e.g.
    lilac (34 rows) got a huge multiplier, so the old model spammed rare classes
    (lilac/peach showed recall 1.0 but precision 0.15-0.36). Taking the sqrt
    softens the extremes, and we cap the ratio so no class dominates the loss.
    """
    classes = np.unique(y)
    balanced = compute_class_weight(class_weight="balanced", classes=classes, y=y)
    damped = np.sqrt(balanced)
    damped = damped / damped.mean()            # keep average weight ~1
    damped = np.clip(damped, 1.0 / cap, cap)   # no class >cap or <1/cap
    return {int(c): float(wi) for c, wi in zip(classes, damped)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true", help="3-epoch sanity-check run")
    parser.add_argument("--epochs1", type=int, default=10)
    parser.add_argument("--epochs2", type=int, default=8)
    parser.add_argument("--epochs3", type=int, default=4)
    parser.add_argument("--batch-size", type=int, default=24)
    args = parser.parse_args()

    if args.quick:
        args.epochs1, args.epochs2, args.epochs3 = 1, 1, 1
        args.batch_size = 16

    os.makedirs(ART_DIR, exist_ok=True)
    set_seeds()

    if not os.path.exists(TRAIN_CSV):
        raise SystemExit(
            f"{TRAIN_CSV} not found. Run prepare_training_data.py first."
        )

    df = pd.read_csv(TRAIN_CSV)
    df = df[df["seg_path"].astype(bool)].reset_index(drop=True)
    # Resolve seg paths relative to this script's folder so the same CSV works
    # both locally (absolute paths) and on Colab (relative 'images_seg/x.png').
    df["seg_path"] = df["seg_path"].apply(
        lambda p: p if os.path.isabs(str(p)) else os.path.join(BASE_DIR, str(p))
    )
    df = df[df["seg_path"].apply(os.path.exists)].reset_index(drop=True)
    if len(df) < 200:
        raise SystemExit(f"Too few usable rows ({len(df)}).")

    color_enc = LabelEncoder()
    design_enc = LabelEncoder()
    yc = color_enc.fit_transform(df["colour"].values).astype(np.int32)
    yd = design_enc.fit_transform(df["design"].values).astype(np.int32)
    print(f"Rows: {len(df)}  |  colors: {len(color_enc.classes_)}  |  designs: {len(design_enc.classes_)}")

    # Stratify on the harder, smaller-class target (design)
    idx = np.arange(len(df))
    train_idx, val_idx = train_test_split(
        idx, test_size=0.15, random_state=SEED, stratify=yd
    )
    print(f"Train: {len(train_idx)}, Val: {len(val_idx)}")

    paths = df["seg_path"].values
    color_weights = compute_weights(yc[train_idx])
    design_weights = compute_weights(yd[train_idx])

    train_ds = make_dataset(
        paths[train_idx],
        yc[train_idx],
        yd[train_idx],
        args.batch_size,
        training=True,
    )
    val_ds = make_dataset(
        paths[val_idx],
        yc[val_idx],
        yd[val_idx],
        args.batch_size,
        training=False,
    )

    # ----- Custom class-weighted loss (Keras 3 friendly) -----
    def make_weighted_loss(weights_dict: dict[int, float], num_classes: int):
        """Return a sparse-categorical-crossentropy that multiplies each
        sample's loss by the class weight of its true label."""
        wvec = np.ones(num_classes, dtype=np.float32)
        for k, v in weights_dict.items():
            if 0 <= int(k) < num_classes:
                wvec[int(k)] = float(v)
        w_const = tf.constant(wvec, dtype=tf.float32)

        def loss_fn(y_true, y_pred):
            y_true_i = tf.cast(tf.reshape(y_true, [-1]), tf.int32)
            ce = tf.keras.losses.sparse_categorical_crossentropy(y_true, y_pred)
            sw = tf.gather(w_const, y_true_i)
            sw = tf.reshape(sw, tf.shape(ce))
            return ce * sw

        return loss_fn

    color_loss_fn = make_weighted_loss(color_weights, len(color_enc.classes_))
    design_loss_fn = make_weighted_loss(design_weights, len(design_enc.classes_))

    model, base = build_model(len(color_enc.classes_), len(design_enc.classes_))

    cbs = [
        tf.keras.callbacks.EarlyStopping(
            monitor="val_loss", patience=4, restore_best_weights=True
        ),
        tf.keras.callbacks.ReduceLROnPlateau(
            monitor="val_loss", factor=0.5, patience=2, min_lr=1e-7
        ),
        tf.keras.callbacks.ModelCheckpoint(
            MODEL_PATH, monitor="val_loss", save_best_only=True
        ),
    ]

    def compile_(lr: float) -> None:
        model.compile(
            optimizer=tf.keras.optimizers.Adam(lr),
            loss={"color": color_loss_fn, "design": design_loss_fn},
            loss_weights={"color": 1.0, "design": 1.0},
            metrics={"color": ["accuracy"], "design": ["accuracy"]},
        )

    # ------------------- Phase 1: heads only -------------------
    print("\n=== Phase 1: head-only training (backbone frozen) ===")
    base.trainable = False
    compile_(1e-3)
    model.fit(
        train_ds,
        validation_data=val_ds,
        epochs=args.epochs1,
        callbacks=cbs,
        verbose=1,
    )

    # ------------------- Phase 2: unfreeze top -------------------
    print("\n=== Phase 2: unfreezing top 40 layers ===")
    base.trainable = True
    for l in base.layers[:-40]:
        l.trainable = False
    compile_(1e-4)
    model.fit(
        train_ds,
        validation_data=val_ds,
        epochs=args.epochs2,
        callbacks=cbs,
        verbose=1,
    )

    # ------------------- Phase 3: full fine-tune -------------------
    print("\n=== Phase 3: full fine-tune ===")
    base.trainable = True
    for l in base.layers:
        l.trainable = True
    compile_(1e-5)
    model.fit(
        train_ds,
        validation_data=val_ds,
        epochs=args.epochs3,
        callbacks=cbs,
        verbose=1,
    )

    # ------------------- Save artifacts -------------------
    model.save(MODEL_PATH)
    with open(ENC_PATH, "wb") as f:
        pickle.dump({"color": color_enc, "design": design_enc}, f)
    print(f"\nSaved {MODEL_PATH}")
    print(f"Saved {ENC_PATH}")

    # ------------------- Evaluation report -------------------
    print("\nRunning validation evaluation for the report...")
    y_color_true: list[int] = []
    y_color_pred: list[int] = []
    y_design_true: list[int] = []
    y_design_pred: list[int] = []
    for x, y in val_ds:
        pc, pd_ = model.predict(x, verbose=0)
        y_color_true.extend(y["color"].numpy().tolist())
        y_design_true.extend(y["design"].numpy().tolist())
        y_color_pred.extend(np.argmax(pc, axis=1).tolist())
        y_design_pred.extend(np.argmax(pd_, axis=1).tolist())

    color_acc = accuracy_score(y_color_true, y_color_pred)
    design_acc = accuracy_score(y_design_true, y_design_pred)
    print(f"Color acc:  {color_acc:.3f}")
    print(f"Design acc: {design_acc:.3f}")

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(f"Color acc:  {color_acc:.4f}\n")
        f.write(f"Design acc: {design_acc:.4f}\n\n")
        f.write("=== Per-class color report ===\n")
        f.write(
            classification_report(
                y_color_true,
                y_color_pred,
                target_names=list(color_enc.classes_),
                zero_division=0,
            )
        )
        f.write("\n\n=== Per-class design report ===\n")
        f.write(
            classification_report(
                y_design_true,
                y_design_pred,
                target_names=list(design_enc.classes_),
                zero_division=0,
            )
        )
    print(f"Wrote {REPORT_PATH}")


if __name__ == "__main__":
    main()
