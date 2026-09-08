# -*- coding: utf-8 -*-
"""Figure: benchmark redundancy audit + the content-ablation streams.

Panels
 (a) calibration: Hamming distance for 429 ground-truth same-scan pairs vs random pairs
 (b) an example provenance-duplicate pair (same scan, two filenames)
 (c) redundancy vs threshold: fraction of images in a multi-image group, and
     ground-truth pair recall, showing the operating point
 (d-g) the four content streams used in the shortcut probe
"""
import os, json, csv, re
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image

import sys, os as _os
sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _config import ROOT, DATA, RESULTS, FIGS

DATA = DATA; IMG = os.path.join(DATA, "images")
MB = os.path.join(DATA, "mask_brain"); MH = os.path.join(DATA, "mask_head")
RES = RESULTS; OUT = FIGS
os.makedirs(OUT, exist_ok=True)
plt.rcParams.update({"font.size": 7, "font.family": "serif", "axes.linewidth": 0.6,
                     "xtick.major.width": 0.6, "ytick.major.width": 0.6})

rows = list(csv.DictReader(open(os.path.join(DATA, "manifest_raw.csv"), encoding="utf-8")))
stats = json.load(open(os.path.join(RES, "dup_stats.json")))
bits = np.load(os.path.join(RES, "dhash_bits.npy"))
packed = np.packbits(bits, axis=1)
POP = np.unpackbits(np.arange(256, dtype=np.uint8)[:, None], axis=1).sum(1).astype(np.int16)

num, oth = {}, {}
for i, r in enumerate(rows):
    b = os.path.splitext(r["orig"])[0]
    if b.isdigit(): num[int(b)] = i
    else:
        m = re.search(r"(\d+)$", b)
        if m: oth[int(m.group(1))] = i
gt = [(num[k], oth[k]) for k in sorted(set(num) & set(oth))]
gt_d = np.array([int(POP[np.bitwise_xor(packed[a], packed[b])].sum()) for a, b in gt])
rng = np.random.default_rng(0)
ra, rb = rng.integers(0, len(rows), 20000), rng.integers(0, len(rows), 20000)
k = ra != rb
rnd_d = np.array([int(POP[np.bitwise_xor(packed[a], packed[b])].sum())
                  for a, b in zip(ra[k], rb[k])])

fig = plt.figure(figsize=(7.16, 3.25))
gs = fig.add_gridspec(2, 4, height_ratios=[1.15, 1.0], hspace=0.72, wspace=0.35)

# (a) calibration
ax = fig.add_subplot(gs[0, 0])
ax.hist(rnd_d, bins=60, color="0.72", label="random pairs", density=True)
ax.hist(gt_d, bins=np.arange(0, 20), color="#b2182b", label="same-scan pairs\n(n=429)", density=True)
ax.axvline(6, color="k", ls="--", lw=0.8)
ax.set_xlim(-5, 150)
ax.annotate("threshold 6", xy=(7, ax.get_ylim()[1]*0.45),
            xytext=(34, ax.get_ylim()[1]*0.60), fontsize=5.5,
            arrowprops=dict(arrowstyle="->", lw=0.5))
ax.set_xlabel("Hamming distance (256-bit dHash)"); ax.set_ylabel("density")
ax.set_title("(a) detector calibration", fontsize=7.5)
ax.legend(fontsize=5, frameon=False, loc="upper right", handlelength=1.2)

# (b) example duplicate pair
ax = fig.add_subplot(gs[0, 1])
i0, i1 = gt[0]
a = np.array(Image.open(os.path.join(IMG, rows[i0]["file"])).resize((150, 150)))
b = np.array(Image.open(os.path.join(IMG, rows[i1]["file"])).resize((150, 150)))
ax.imshow(np.concatenate([a, np.full((150, 6), 255, np.uint8), b], 1), cmap="gray")
ax.set_xticks([]); ax.set_yticks([])
ax.set_title("(b) duplicate pair", fontsize=7.5, pad=3)
ax.set_xlabel(f"{rows[i0]['orig']}   |   {rows[i1]['orig']}", fontsize=5)

# (c) redundancy vs threshold
ax = fig.add_subplot(gs[0, 2:])
T = sorted(int(t) for t in stats["stats"])
frac = [stats["stats"][str(t)]["frac_in_multi_groups"] * 100 for t in T]
rec = [stats["stats"][str(t)]["gt_pair_recall"] * 100 for t in T]
ax.plot(T, frac, "o-", ms=2.5, lw=1.0, color="#2166ac", label="images in a redundancy group (%)")
ax.plot(T, rec, "s--", ms=2.5, lw=1.0, color="#b2182b", label="same-scan pairs recovered (%)")
ax.axvline(6, color="k", ls="--", lw=0.8)
ax.set_xlabel("near-duplicate threshold (Hamming)"); ax.set_ylabel("%")
ax.set_title("(c) redundancy and detector recall vs threshold", fontsize=7.5)
ax.legend(fontsize=5.5, frameon=False, loc="center right"); ax.set_ylim(-3, 118)
ax.grid(alpha=0.25, lw=0.4)

# (d)-(g) content streams
ex = 1500
g = np.array(Image.open(os.path.join(IMG, rows[ex]["file"])).convert("L"))
mb = np.array(Image.open(os.path.join(MB, rows[ex]["file"]))) > 0
mh = np.array(Image.open(os.path.join(MH, rows[ex]["file"]))) > 0
streams = [("(d) full slice", g),
           ("(e) brain", np.where(mb, g, 0)),
           ("(f) non-brain", np.where(~mb & mh, g, 0)),
           ("(g) exterior", np.where(~mh, g, 0))]
for j, (t, im) in enumerate(streams):
    ax = fig.add_subplot(gs[1, j])
    ax.imshow(im, cmap="gray", vmin=0, vmax=255)
    ax.set_xticks([]); ax.set_yticks([]); ax.set_title(t, fontsize=7)

fig.savefig(os.path.join(OUT, "fig_audit.png"), dpi=600, bbox_inches="tight")
print("wrote fig_audit.png")
