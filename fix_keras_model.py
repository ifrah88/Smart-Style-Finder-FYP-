"""
Make a Colab-trained .keras model loadable in the local environment.

Colab ships a newer Keras than the local venv (TF 2.19 / Keras 3.12). The newer
Keras writes a `quantization_config` field into layer configs that the local
Keras doesn't recognise, so `load_model` fails with:
    Unrecognized keyword arguments passed to Dense: {'quantization_config': None}

This strips that field from the model's config.json (a .keras file is just a zip
of config.json + weights), leaving the weights untouched, then verifies it loads.

Usage:
    python fix_keras_model.py [path/to/model.keras]   # default: artifacts/dress_multitask_tf.keras
"""
from __future__ import annotations

import json
import os
import sys
import zipfile

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT = os.path.join(BASE_DIR, "artifacts", "dress_multitask_tf.keras")
STRIP_KEYS = ("quantization_config",)


def _strip(obj):
    if isinstance(obj, dict):
        for k in STRIP_KEYS:
            obj.pop(k, None)
        for v in obj.values():
            _strip(v)
    elif isinstance(obj, list):
        for v in obj:
            _strip(v)


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else DEFAULT
    if not os.path.exists(src):
        raise SystemExit(f"Not found: {src}")

    with zipfile.ZipFile(src) as z:
        names = z.namelist()
        data = {n: z.read(n) for n in names}

    if b"quantization_config" not in data.get("config.json", b""):
        print("No quantization_config found — model already compatible.")
        return

    cfg = json.loads(data["config.json"].decode("utf-8"))
    _strip(cfg)
    data["config.json"] = json.dumps(cfg).encode("utf-8")

    tmp = src + ".tmp"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        for n in names:
            z.writestr(n, data[n])

    # verify before replacing
    import tensorflow as tf  # noqa
    m = tf.keras.models.load_model(tmp, compile=False)
    os.replace(tmp, src)
    print(f"Fixed and verified: {src}")
    print(f"  inputs {m.input_shape}  outputs {[tuple(o.shape) for o in m.outputs]}")


if __name__ == "__main__":
    main()
