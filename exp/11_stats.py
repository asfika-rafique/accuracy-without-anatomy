# -*- coding: utf-8 -*-
"""Paired bootstrap tests on the key contrasts, plus a sensitivity analysis
restricted to slices with a reliable intracranial mask.

Contrasts tested (all on the pooled held-out test predictions, grouped policy):
  full     vs brain      -- cost of restricting input to the intracranial compartment
  brain    vs non-brain  -- is lesion-free content as informative as brain content?
  exterior vs chance     -- does patient-free content carry label information?
"""
import os, glob, json
import numpy as np
from sklearn.metrics import roc_auc_score

import sys, os as _os
sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _config import ROOT, RESULTS, RUNS

ROOT = ROOT; RES = RESULTS
RUNS = os.path.join(RES, "runs")
B = 10000
rng = np.random.default_rng(0)


def load(stream, seed):
    f = os.path.join(RUNS, f"resnet18_grouped_{stream}_s{seed}_preds.npz")
    d = np.load(f); o = np.argsort(d["I"])
    return d["P"][o], d["Y"][o], d["I"][o]


def macro_auc(P, Y):
    a = []
    for c in range(3):
        yb = (Y == c).astype(int)
        if yb.min() != yb.max():
            a.append(roc_auc_score(yb, P[:, c]))
    return float(np.mean(a)) if a else np.nan


def paired_boot(sA, sB, metric="acc"):
    """Paired bootstrap over the SAME test images, pooled across the three seeds."""
    dif, aV, bV = [], [], []
    for seed in (0, 1, 2):
        PA, YA, IA = load(sA, seed); PB, YB, IB = load(sB, seed)
        assert (IA == IB).all() and (YA == YB).all()
        n = len(YA)
        for _ in range(B // 3):
            i = rng.integers(0, n, n)
            if metric == "acc":
                a = float((PA[i].argmax(1) == YA[i]).mean())
                b = float((PB[i].argmax(1) == YB[i]).mean())
            else:
                a = macro_auc(PA[i], YA[i]); b = macro_auc(PB[i], YB[i])
            dif.append(a - b); aV.append(a); bV.append(b)
    dif = np.array(dif)
    return dict(mean_A=float(np.mean(aV)), mean_B=float(np.mean(bV)),
                delta=float(dif.mean()),
                ci=[float(np.percentile(dif, 2.5)), float(np.percentile(dif, 97.5))],
                p_two_sided=float(2 * min((dif <= 0).mean(), (dif >= 0).mean())))


out = {}
print("PAIRED BOOTSTRAP CONTRASTS (accuracy, 10000 resamples, pooled over 3 seeds)")
for a, b in [("full", "brain"), ("brain", "nonbrain"), ("full", "nonbrain"),
             ("nonbrain", "exterior")]:
    r = paired_boot(a, b, "acc")
    out[f"{a}_vs_{b}_acc"] = r
    print(f"  {a:9s} - {b:9s}: {r['mean_A']:.4f} - {r['mean_B']:.4f} = {r['delta']:+.4f} "
          f"[{r['ci'][0]:+.4f}, {r['ci'][1]:+.4f}]  p={r['p_two_sided']:.4f}")

print("\nEXTERIOR STREAM vs CHANCE (macro-AUC)")
vals = []
for seed in (0, 1, 2):
    P, Y, _ = load("exterior", seed)
    n = len(Y)
    for _ in range(B // 3):
        i = rng.integers(0, n, n)
        vals.append(macro_auc(P[i], Y[i]))
vals = np.array(vals)
out["exterior_macro_auc"] = dict(mean=float(vals.mean()),
                                 ci=[float(np.percentile(vals, 2.5)),
                                     float(np.percentile(vals, 97.5))],
                                 chance=0.5)
print(f"  macro-AUC {vals.mean():.4f} [{np.percentile(vals,2.5):.4f}, "
      f"{np.percentile(vals,97.5):.4f}]  vs chance 0.5")

# ---------- sensitivity: restrict to slices with a reliable brain mask -------
frac = np.load(os.path.join(RES, "brain_frac.npy"))
print("\nSENSITIVITY: slices with an unreliable (near-empty) intracranial mask excluded")
sens = {}
for st in ("full", "brain", "nonbrain", "exterior"):
    accs, aucs, ns = [], [], []
    for seed in (0, 1, 2):
        P, Y, I = load(st, seed)
        keep = frac[I] >= 0.02
        accs.append(float((P[keep].argmax(1) == Y[keep]).mean()))
        aucs.append(macro_auc(P[keep], Y[keep])); ns.append(int(keep.sum()))
    sens[st] = dict(n=int(np.mean(ns)), acc=float(np.mean(accs)), auc=float(np.mean(aucs)))
    print(f"  {st:9s} n~{int(np.mean(ns)):4d}  acc {np.mean(accs):.4f}  macro-AUC {np.mean(aucs):.4f}")
out["sensitivity_reliable_mask"] = sens

json.dump(out, open(os.path.join(RES, "stats.json"), "w"), indent=2)
print("\nsaved stats.json")
