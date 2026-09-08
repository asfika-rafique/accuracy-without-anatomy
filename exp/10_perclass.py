# -*- coding: utf-8 -*-
"""Per-class breakdown of the content ablation, agreement between the full-slice
and lesion-free models, and a metadata-only shortcut check.

All computed from saved predictions and the manifest; no retraining.
"""
import os, csv, json, glob
import numpy as np
from collections import Counter
from sklearn.metrics import roc_auc_score, confusion_matrix

import sys, os as _os
sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _config import ROOT, DATA, RESULTS, RUNS

ROOT = ROOT; RES = RESULTS
RUNS = os.path.join(RES, "runs"); DATA = DATA
CLS = ["hemorrhagic", "ischemic", "normal"]
out = {}

# ---------- 1. per-class metrics per stream ---------------------------------
print("PER-CLASS RESULTS (ResNet-18, grouped split, 3 seeds pooled)")
print(f"{'stream':10s} " + " ".join(f"{c[:10]:>22s}" for c in CLS))
percls = {}
for st in ("full", "brain", "nonbrain", "exterior"):
    fs = [f for f in sorted(glob.glob(os.path.join(RUNS, f"resnet18_grouped_{st}_s*_preds.npz")))
          if "nodcm" not in f and "perm" not in f]
    if not fs:
        continue
    P = np.concatenate([np.load(f)["P"] for f in fs])
    Y = np.concatenate([np.load(f)["Y"] for f in fs])
    pred = P.argmax(1)
    row, cells = {}, []
    for c, name in enumerate(CLS):
        m = Y == c
        rec = float((pred[m] == c).mean())
        auc = float(roc_auc_score((Y == c).astype(int), P[:, c]))
        row[name] = dict(recall=rec, auc=auc, n=int(m.sum()))
        cells.append(f"rec {rec:.3f} / AUC {auc:.3f}")
    percls[st] = row
    print(f"{st:10s} " + " ".join(f"{x:>22s}" for x in cells))
    cm = confusion_matrix(Y, pred, labels=[0, 1, 2])
    row["confusion"] = cm.tolist()
out["per_class"] = percls

print("\nConfusion matrix, full-slice (rows = truth h/i/n):")
for r in percls["full"]["confusion"]:
    print("   ", r)
print("Confusion matrix, exterior-only:")
for r in percls["exterior"]["confusion"]:
    print("   ", r)

# ---------- 2. agreement between full-slice and lesion-free models ----------
def stack(st, seed):
    f = os.path.join(RUNS, f"resnet18_grouped_{st}_s{seed}_preds.npz")
    d = np.load(f); o = np.argsort(d["I"])
    return d["P"][o], d["Y"][o], d["I"][o]

agree = []
for seed in (0, 1, 2):
    Pf, Yf, If = stack("full", seed)
    Pn, Yn, In = stack("nonbrain", seed)
    assert (If == In).all()
    af, an = Pf.argmax(1), Pn.argmax(1)
    agree.append(dict(seed=seed,
                      agreement=float((af == an).mean()),
                      full_correct=float((af == Yf).mean()),
                      nonbrain_correct=float((an == Yf).mean()),
                      both_correct=float(((af == Yf) & (an == Yf)).mean()),
                      full_right_nonbrain_wrong=float(((af == Yf) & (an != Yf)).mean()),
                      nonbrain_right_full_wrong=float(((an == Yf) & (af != Yf)).mean())))
A = {k: float(np.mean([a[k] for a in agree])) for k in agree[0] if k != "seed"}
out["full_vs_nonbrain_agreement"] = A
print("\nAGREEMENT full-slice vs lesion-free (non-brain) model, mean over 3 seeds:")
for k, v in A.items():
    print(f"   {k:28s} {v:.4f}")

# ---------- 3. metadata-only shortcut: does image geometry encode the class? -
rows = list(csv.DictReader(open(os.path.join(DATA, "manifest_raw.csv"), encoding="utf-8")))
by = {c: Counter() for c in CLS}
for r in rows:
    by[r["cls"]][(int(r["w"]), int(r["h"]))] += 1
print("\nIMAGE GEOMETRY BY CLASS (top sizes)")
sq = {}
for c in CLS:
    tot = sum(by[c].values())
    n512 = by[c][(512, 512)]
    sq[c] = dict(n=tot, square512=n512, frac_square512=n512 / tot)
    print(f"   {c:12s} n={tot:5d}  512x512: {n512:5d} ({n512/tot:.3f})  "
          f"other sizes: {tot-n512:4d}")
out["geometry_by_class"] = sq

# a one-rule classifier using only "is the image non-square 512x512"
nonsq = np.array([not (int(r["w"]) == 512 and int(r["h"]) == 512) for r in rows])
lab = np.array([CLS.index(r["cls"]) for r in rows])
print("\n   non-512x512 images by class:", {CLS[c]: int(nonsq[lab == c].sum()) for c in range(3)})
out["nonsquare_by_class"] = {CLS[c]: int(nonsq[lab == c].sum()) for c in range(3)}

json.dump(out, open(os.path.join(RES, "perclass.json"), "w"), indent=2)
print("\nsaved perclass.json")
