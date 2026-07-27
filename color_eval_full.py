"""
COMPLETE colour evaluation for the fashion retrieval engine.

Runs entirely on the precomputed artifacts (clip_db + color_palette + the old
color_feats), using dataset items as queries -- no CLIP model needed, so it is
fast and fully reproducible.

Sections:
  A. Palette statistics            -- how many colours per garment, coverage
  B. Detection accuracy            -- palette colour names vs CSV labels
  C. Detection confusion           -- what each true colour is predicted as
  D. Matching: OLD vs NEW          -- mean-Lab re-rank vs palette re-rank, both
                                      fused with CLIP, swept over alpha
  E. Multi-colour ('multi') items  -- how the 95 multi-labelled items are tagged

Common, descriptor-agnostic matching metric = colour-consistency@k: the share of
top-k results whose CSV colour equals the query's CSV colour. We also report each
engine's native perceptual distance.
"""
from __future__ import annotations

import os
import collections
import numpy as np

from clip_retrieval import ClipRetrieval, SHORTLIST, DELTAE_TAU, _minmax

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COLOR_FEATS = os.path.join(BASE_DIR, "artifacts", "color_feats.npz")
SAMPLE = 800
SEED = 42


# ---- old mean-Lab engine (faithful baseline) ------------------------------
class MeanLabBaseline:
    """The previous colour engine: a single mean-CIELAB per item, re-ranking
    the CLIP shortlist by mean-Lab deltaE."""

    def __init__(self, eng):
        self.E = eng.E
        c = np.load(COLOR_FEATS, allow_pickle=True)
        self.lab = c["lab_mean"].astype(np.float32)

    def search(self, qi, k, alpha):
        sims = self.E @ self.E[qi]
        order = np.argsort(-sims)
        order = order[order != qi]
        shortlist = order[:SHORTLIST]
        clip_s = sims[shortlist]
        dE = np.linalg.norm(self.lab[shortlist] - self.lab[qi][None, :], axis=1)
        color_s = np.exp(-dE / DELTAE_TAU)
        combined = (1 - alpha) * _minmax(clip_s) + alpha * _minmax(color_s)
        local = np.argsort(-combined)[:k]
        return shortlist[local], dE[local]


# ---- metrics --------------------------------------------------------------
def consistency_at_k(col, qi, ranked):
    qc = col[qi]
    return float(np.mean([col[r] == qc for r in ranked]))


# ---- A. palette stats -----------------------------------------------------
def palette_stats(eng):
    cnt = eng.pal_counts
    dist = collections.Counter(cnt.tolist())
    dom_w = eng.pal_weights[:, 0]
    print("== A. PALETTE STATISTICS ==")
    print(f"  products: {len(cnt)}")
    for n in (1, 2, 3):
        print(f"  {n}-colour palettes : {dist.get(n,0):4d}  ({dist.get(n,0)/len(cnt):.0%})")
    print(f"  mean dominant weight: {dom_w.mean():.0%}  (avg pixel share of the top colour)")
    print(f"  mean colours/garment: {cnt.mean():.2f}\n")


# ---- B/C. detection -------------------------------------------------------
def detection(eng):
    col = eng.meta["colour"].astype(str)
    names, cnt = eng.pal_names, eng.pal_counts
    sel = np.where(col != "multi")[0]
    n = len(sel)
    top1 = sum(names[i][0] == col[i] for i in sel)
    top3 = sum(col[i] in list(names[i][: int(cnt[i])]) for i in sel)
    print("== B. DETECTION ACCURACY (palette vs CSV labels, 'multi' excluded) ==")
    print(f"  items: {n}")
    print(f"  dominant == CSV label : {top1/n:.1%}")
    print(f"  CSV label in top-3    : {top3/n:.1%}")
    per = {}
    for i in sel:
        a = per.setdefault(col[i], [0, 0]); a[0] += names[i][0] == col[i]; a[1] += 1
    print("  per-colour dominant-match (sorted by frequency):")
    for c in sorted(per, key=lambda k: -per[k][1]):
        a = per[c]; print(f"    {c:<8} {a[0]/a[1]:4.0%}  (n={a[1]})")
    print()

    print("== C. DETECTION CONFUSION (true CSV -> top predicted dominant) ==")
    for c in sorted(per, key=lambda k: -per[k][1]):
        idx = sel[col[sel] == c]
        pred = collections.Counter(names[i][0] for i in idx)
        top = ", ".join(f"{p}:{n_}" for p, n_ in pred.most_common(4))
        print(f"  {c:<8} (n={len(idx)}) -> {top}")
    print()


# ---- D. matching old vs new ----------------------------------------------
def matching(eng):
    col = eng.meta["colour"].astype(str)
    old = MeanLabBaseline(eng)
    rng = np.random.default_rng(SEED)
    qs = rng.choice(len(eng.E), size=min(SAMPLE, len(eng.E)), replace=False)
    alphas = [0.0, 0.3, 0.5, 0.7, 0.9, 1.0]

    print(f"== D. MATCHING QUALITY -- OLD (mean-Lab) vs NEW (palette) ==")
    print(f"  {len(qs)} queries (dataset items, self excluded). Metric = colour-consistency@5.")
    print(f"  {'alpha':>5} | {'OLD cons@5':>10} | {'NEW cons@5':>10} | {'OLD dE@5':>8} | {'NEW dE@5':>8}")
    best = {"old": (0, -1), "new": (0, -1)}
    for a in alphas:
        oc = nc = od = nd = 0.0
        for qi in qs:
            qi = int(qi)
            r_old, dE_old = old.search(qi, 5, a)
            labs, w = eng.query_palette(qi)
            res = eng.search_by_palette(eng.E[qi], labs, w, k=5, alpha=a, exclude_idx=qi)
            r_new = [r["idx"] for r in res]
            oc += consistency_at_k(col, qi, r_old)
            nc += consistency_at_k(col, qi, r_new)
            od += float(np.mean(dE_old))
            nd += float(np.mean([r["color_dist"] for r in res]))
        oc/=len(qs); nc/=len(qs); od/=len(qs); nd/=len(qs)
        if oc>best["old"][1]: best["old"]=(a,oc)
        if nc>best["new"][1]: best["new"]=(a,nc)
        tag = "  <- pure CLIP" if a==0.0 else ""
        print(f"  {a:>5.2f} | {oc:>10.3f} | {nc:>10.3f} | {od:>8.2f} | {nd:>8.2f}{tag}")
    print(f"  best colour-consistency@5: OLD alpha={best['old'][0]} -> {best['old'][1]:.3f}"
          f" | NEW alpha={best['new'][0]} -> {best['new'][1]:.3f}")

    # consistency@1 and recall (query colour anywhere in top-5) at best new alpha
    a = best["new"][0]
    c1 = rec = 0.0
    for qi in qs:
        qi=int(qi)
        labs, w = eng.query_palette(qi)
        res = eng.search_by_palette(eng.E[qi], labs, w, k=5, alpha=a, exclude_idx=qi)
        rn=[r["idx"] for r in res]
        c1 += col[rn[0]]==col[qi]
        rec += any(col[r]==col[qi] for r in rn)
    print(f"  NEW @alpha={a}: colour-consistency@1 = {c1/len(qs):.3f}, "
          f"query-colour-in-top5 = {rec/len(qs):.3f}\n")


# ---- E. multi-colour items ------------------------------------------------
def multi_items(eng):
    col = eng.meta["colour"].astype(str)
    idx = np.where(col == "multi")[0]
    cnt = eng.pal_counts[idx]
    print("== E. 'MULTI'-LABELLED ITEMS (no single ground-truth colour) ==")
    print(f"  count: {len(idx)}")
    print(f"  mean colours detected: {cnt.mean():.2f}  "
          f"(>=2 colours: {(cnt>=2).mean():.0%}, 3 colours: {(cnt==3).mean():.0%})")
    print("  examples (palette tags):")
    for i in idx[:6]:
        c = int(eng.pal_counts[i])
        tags = "+".join(eng.pal_names[i][:c])
        print(f"    {str(eng.meta['product_ids'][i]):<16} {tags}")
    print()


def main():
    eng = ClipRetrieval()
    print(f"\nDATASET: {len(eng.E)} products, {len(set(eng.meta['colour'].astype(str)))} CSV colour labels\n")
    palette_stats(eng)
    detection(eng)
    multi_items(eng)
    matching(eng)


if __name__ == "__main__":
    main()
