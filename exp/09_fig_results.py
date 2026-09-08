# -*- coding: utf-8 -*-
"""Figure: the two measured effects.

 (a) Content ablation -- which image content predicts the diagnostic label
 (b) Redundancy leakage -- test images with vs without a training near-duplicate
 (c) Architecture comparison under the rigorous protocol
"""
import os, json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import sys, os as _os
sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _config import ROOT, RESULTS, FIGS

ROOT = ROOT; RES = RESULTS
OUT = FIGS; os.makedirs(OUT, exist_ok=True)
S = json.load(open(os.path.join(RES, "summary.json")))
plt.rcParams.update({"font.size": 7, "font.family": "serif", "axes.linewidth": 0.6})

fig, axes = plt.subplots(1, 3, figsize=(7.16, 1.95),
                         gridspec_kw=dict(width_ratios=[1.45, 1.0, 1.0], wspace=0.34))

# ---------------- (a) content ablation ------------------------------------
P = S["shortcut_probe"]
order = [("resnet18/full", "full\nslice"), ("resnet18/brain", "brain\nonly"),
         ("resnet18/nonbrain", "non-brain\n(no brain)"),
         ("resnet18/exterior", "exterior\n(no head)")]
acc = [P[k]["acc"] for k, _ in order]
sd = [P[k].get("acc_sd", 0) for k, _ in order]
auc = [P[k]["auc"] for k, _ in order]
aucsd = [P[k].get("auc_sd", 0) for k, _ in order]
x = np.arange(len(order)); w = 0.38
ax = axes[0]
ax.bar(x - w/2, acc, w, yerr=sd, capsize=2, color="#2166ac", label="accuracy",
       error_kw=dict(lw=0.7))
ax.bar(x + w/2, auc, w, yerr=aucsd, capsize=2, color="#92c5de", label="macro-AUC",
       error_kw=dict(lw=0.7))
maj = S["reference"]["majority_class_accuracy"]
ax.axhline(maj, color="#b2182b", ls="--", lw=0.8)
ax.text(3.45, maj + 0.014, "majority class", fontsize=5, color="#b2182b", ha="right")
ax.axhline(0.5, color="0.45", ls=":", lw=0.8)
ax.text(3.42, 0.515, "AUC chance", fontsize=5, color="0.35", ha="right")
perm = S.get("resnet18/grouped/full/True/False")
ax.set_xticks(x); ax.set_xticklabels([l for _, l in order], fontsize=6.2)
ax.set_ylim(0.35, 1.16); ax.set_ylabel("test performance")
ax.set_yticks([0.4,0.5,0.6,0.7,0.8,0.9,1.0])
ax.set_title("(a) which content predicts the label?", fontsize=7.5)
ax.legend(fontsize=5.5, frameon=False, ncol=2, loc="upper center",
          columnspacing=0.9, bbox_to_anchor=(0.5, 1.03))
ax.grid(axis="y", alpha=0.25, lw=0.4)
for xi, v in zip(x - w/2, acc):
    ax.text(xi, v + 0.012, f"{v:.3f}", ha="center", fontsize=4.8)

# ---------------- (b) leakage ---------------------------------------------
ax = axes[1]
W = S["within_run_leakage"]
archs = ["densenet201", "resnet18"]
lk = [W[a]["leaked_acc"] for a in archs]
cl = [W[a]["clean_acc"] for a in archs]
x = np.arange(len(archs)); w = 0.36
ax.bar(x - w/2, lk, w, color="#b2182b", label="has train near-duplicate")
ax.bar(x + w/2, cl, w, color="0.72", label="no near-duplicate")
for xi, v in zip(x - w/2, lk): ax.text(xi, v + 0.002, f"{v:.3f}", ha="center", fontsize=4.8)
for xi, v in zip(x + w/2, cl): ax.text(xi, v + 0.002, f"{v:.3f}", ha="center", fontsize=4.8)
ax.set_xticks(x); ax.set_xticklabels(["DenseNet-201", "ResNet-18"], fontsize=6)
ax.set_ylim(0.94, 1.012); ax.set_ylabel("test accuracy")
ax.set_title("(b) redundancy leakage\n(random split, stratified)", fontsize=7.5)
ax.legend(fontsize=5.2, frameon=False, loc="lower left", framealpha=0)
ax.grid(axis="y", alpha=0.25, lw=0.4)

# ---------------- (c) architectures ---------------------------------------
ax = axes[2]
CI = S["bootstrap_ci"]
keys = [("densenet201/grouped", "DenseNet-201"), ("resnet50/grouped", "ResNet-50"),
        ("resnet18/grouped", "ResNet-18")]
v = [CI[k]["accuracy"][0] for k, _ in keys]
lo = [CI[k]["accuracy"][0] - CI[k]["accuracy"][1] for k, _ in keys]
hi = [CI[k]["accuracy"][2] - CI[k]["accuracy"][0] for k, _ in keys]
y = np.arange(len(keys))
ax.errorbar(v, y, xerr=[lo, hi], fmt="o", ms=3.5, lw=1.0, capsize=2.5, color="#2166ac")
ax.set_yticks(y); ax.set_yticklabels([l for _, l in keys], fontsize=6)
ax.set_xlim(0.955, 0.98); ax.invert_yaxis()
ax.set_xlabel("test accuracy (95% bootstrap CI)", fontsize=6)
ax.set_title("(c) architecture is not\nthe limiting factor", fontsize=7.5)
ax.grid(axis="x", alpha=0.25, lw=0.4)

fig.savefig(os.path.join(OUT, "fig_results.png"), dpi=600, bbox_inches="tight")
print("wrote fig_results.png")
