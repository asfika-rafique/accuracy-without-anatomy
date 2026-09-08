# -*- coding: utf-8 -*-
"""Build the two split policies compared in the paper.

policy = "random"   image-level stratified split  (what the original study, and
                    most published work on this collection, effectively does)
policy = "grouped"  redundancy-aware split: every near-duplicate group is kept
                    entirely inside one partition

Proportions 70 / 15 / 15 train / val / test, stratified on the class label.
Model selection uses val only; test is touched once, at the end.
"""
import os, csv, json, sys
import numpy as np

import sys, os as _os
sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _config import ROOT, DATA, RESULTS

DATA = DATA; RES = RESULTS
GROUP_FILE = os.path.join(RES, "embgroups_94.csv")   # 100% GT recall, max group 18
FRAC = (0.70, 0.15, 0.15)


def load():
    rows = list(csv.DictReader(open(os.path.join(DATA, "manifest_raw.csv"), encoding="utf-8")))
    grp = {}
    for r in csv.DictReader(open(GROUP_FILE)):
        grp[int(r["idx"])] = int(r["group"])
    return rows, grp


def split_random(rows, seed):
    rng = np.random.default_rng(seed)
    lab = np.array([int(r["label"]) for r in rows])
    assign = np.empty(len(rows), dtype=object)
    for c in np.unique(lab):
        idx = np.where(lab == c)[0]; rng.shuffle(idx)
        a = int(len(idx) * FRAC[0]); b = a + int(len(idx) * FRAC[1])
        assign[idx[:a]] = "train"; assign[idx[a:b]] = "val"; assign[idx[b:]] = "test"
    return assign


def split_grouped(rows, grp, seed):
    """Greedy stratified group assignment: process groups in random order, put
    each into whichever partition is furthest below its per-class quota."""
    rng = np.random.default_rng(seed)
    lab = np.array([int(r["label"]) for r in rows])
    n = len(rows)
    groups = {}
    for i in range(n):
        groups.setdefault(grp[i], []).append(i)
    gids = list(groups); rng.shuffle(gids)

    target = {p: np.array([ (lab == c).sum() * f for c in range(3) ])
              for p, f in zip(("train", "val", "test"), FRAC)}
    have = {p: np.zeros(3) for p in target}
    assign = np.empty(n, dtype=object)
    for g in gids:
        mem = groups[g]
        cnt = np.bincount([lab[i] for i in mem], minlength=3)
        # deficit = how far each partition is below quota, normalised
        best, bestscore = None, None
        for p in ("train", "val", "test"):
            deficit = (target[p] - have[p]) / np.maximum(target[p], 1)
            score = float((deficit * cnt).sum())
            if bestscore is None or score > bestscore:
                best, bestscore = p, score
        for i in mem:
            assign[i] = best
        have[best] += cnt
    return assign


def report(name, rows, assign, grp):
    lab = np.array([int(r["label"]) for r in rows])
    out = {}
    for p in ("train", "val", "test"):
        m = assign == p
        out[p] = dict(n=int(m.sum()),
                      hemorrhagic=int((lab[m] == 0).sum()),
                      ischemic=int((lab[m] == 1).sum()),
                      normal=int((lab[m] == 2).sum()))
    # how many groups are split across partitions?
    gp = {}
    for i, g in grp.items():
        gp.setdefault(g, set()).add(assign[i])
    broken = sum(1 for v in gp.values() if len(v) > 1)
    # how many TEST images have a near-duplicate in TRAIN?
    tr = {g for i, g in grp.items() if assign[i] == "train"}
    leaked = sum(1 for i, g in grp.items() if assign[i] == "test" and g in tr)
    out["groups_split_across_partitions"] = broken
    out["test_images_with_train_near_duplicate"] = leaked
    out["frac_test_leaked"] = leaked / max(1, out["test"]["n"])
    print(name, json.dumps(out, indent=None))
    return out


def main():
    rows, grp = load()
    summary = {}
    for seed in (0, 1, 2):
        for policy in ("random", "grouped"):
            a = split_random(rows, seed) if policy == "random" else split_grouped(rows, grp, seed)
            summary[f"{policy}_s{seed}"] = report(f"{policy} seed{seed}:", rows, a, grp)
            with open(os.path.join(RES, f"split_{policy}_s{seed}.csv"), "w", newline="") as fh:
                w = csv.writer(fh); w.writerow(["idx", "file", "label", "cls", "group", "part"])
                for i, r in enumerate(rows):
                    w.writerow([i, r["file"], r["label"], r["cls"], grp[i], a[i]])
    json.dump(summary, open(os.path.join(RES, "split_summary.json"), "w"), indent=2)
    print("saved split_summary.json")


if __name__ == "__main__":
    main()
