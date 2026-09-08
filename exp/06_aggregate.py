# -*- coding: utf-8 -*-
"""Aggregate all runs: mean +/- SD across seeds, bootstrap CIs, and the
leakage-effect estimates. Writes _results/summary.json and prints paper tables.
"""
import os, json, glob, itertools
import numpy as np

import sys, os as _os
sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _config import ROOT, RESULTS, RUNS, DATA

ROOT = ROOT; RES = RESULTS
RUNS = os.path.join(RES, "runs")
B = 5000
rng = np.random.default_rng(0)


def boot_ci(P, Y, fn, B=B):
    n = len(Y); vals = np.empty(B)
    for b in range(B):
        i = rng.integers(0, n, n)
        try: vals[b] = fn(P[i], Y[i])
        except Exception: vals[b] = np.nan
    v = vals[~np.isnan(vals)]
    return float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))


def acc(P, Y): return float((P.argmax(1) == Y).mean())


def macro_f1(P, Y):
    from sklearn.metrics import f1_score
    return float(f1_score(Y, P.argmax(1), average="macro"))


def macro_auc(P, Y):
    from sklearn.metrics import roc_auc_score
    a = []
    for c in range(3):
        yb = (Y == c).astype(int)
        if yb.min() != yb.max(): a.append(roc_auc_score(yb, P[:, c]))
    return float(np.mean(a)) if a else float("nan")


def main():
    runs = {}
    for f in sorted(glob.glob(os.path.join(RUNS, "*.json"))):
        r = json.load(open(f))
        key = (r["arch"], r["policy"], r["stream"], r["permuted_labels"],
               bool(r.get("exclude_dcm", False)))
        runs.setdefault(key, []).append(r)

    summary = {}
    print(f"{'configuration':44s} {'acc':>16s} {'macroF1':>16s} {'macroAUC':>16s}  seeds")
    print("-" * 100)
    for key in sorted(runs, key=lambda k: (k[0], k[1], k[2], k[3], k[4])):
        rs = runs[key]
        a = np.array([r["test"]["accuracy"] for r in rs])
        f1 = np.array([r["test"]["macro_f1"] for r in rs])
        au = np.array([r["test"]["macro_auc"] for r in rs])
        name = (f"{key[0]} | {key[1]} | {key[2]}" + (" | PERMUTED" if key[3] else "")
                + (" | no-dup-subset" if key[4] else ""))
        summary["/".join(map(str, key))] = dict(
            n_seeds=len(rs),
            accuracy_mean=float(a.mean()), accuracy_sd=float(a.std(ddof=1)) if len(a) > 1 else 0.0,
            macro_f1_mean=float(f1.mean()), macro_f1_sd=float(f1.std(ddof=1)) if len(f1) > 1 else 0.0,
            macro_auc_mean=float(au.mean()), macro_auc_sd=float(au.std(ddof=1)) if len(au) > 1 else 0.0,
            per_seed=dict(accuracy=a.tolist(), macro_f1=f1.tolist(), macro_auc=au.tolist()),
            per_class_accuracy_mean=np.mean([r["test"]["per_class_accuracy"] for r in rs], 0).tolist(),
            auc_by_class_mean={k: float(np.mean([r["test"]["auc"][k] for r in rs]))
                               for k in rs[0]["test"]["auc"]},
            best_epochs=[r["best_epoch"] for r in rs])
        sd = lambda v: f"{v.mean():.4f}+-{(v.std(ddof=1) if len(v)>1 else 0):.4f}"
        print(f"{name:44s} {sd(a):>16s} {sd(f1):>16s} {sd(au):>16s}  {len(rs)}")

    # ---------------- leakage effect -----------------------------------------
    print("\n" + "=" * 100)
    print("LEAKAGE EFFECT  (identical model / protocol; only the split policy differs)")
    lk = {}
    for arch in sorted({k[0] for k in runs}):
        kr, kg = (arch, "random", "full", False, False), (arch, "grouped", "full", False, False)
        if kr in runs and kg in runs:
            ar = np.array([r["test"]["accuracy"] for r in runs[kr]])
            ag = np.array([r["test"]["accuracy"] for r in runs[kg]])
            fr = np.array([r["test"]["macro_f1"] for r in runs[kr]])
            fg = np.array([r["test"]["macro_f1"] for r in runs[kg]])
            lk[arch] = dict(random_acc=float(ar.mean()), grouped_acc=float(ag.mean()),
                            delta_acc_pp=float((ar.mean() - ag.mean()) * 100),
                            random_f1=float(fr.mean()), grouped_f1=float(fg.mean()),
                            delta_f1_pp=float((fr.mean() - fg.mean()) * 100))
            print(f"  {arch:14s} random {ar.mean():.4f} vs grouped {ag.mean():.4f}  "
                  f"-> +{(ar.mean()-ag.mean())*100:+.2f} pp accuracy, "
                  f"{(fr.mean()-fg.mean())*100:+.2f} pp macro-F1")
    summary["leakage_effect"] = lk

    # within-run stratification on the random split
    print("\nWITHIN-RUN STRATIFICATION (random split: test images WITH vs WITHOUT a "
          "near-duplicate in train)")
    strat = {}
    for arch in sorted({k[0] for k in runs}):
        k = (arch, "random", "full", False, False)
        if k not in runs: continue
        L = [r["test_by_leakage"] for r in runs[k]]
        if not all("accuracy" in x.get("leaked", {}) for x in L): continue
        la = np.array([x["leaked"]["accuracy"] for x in L])
        ca = np.array([x["clean"]["accuracy"] for x in L])
        ln = int(np.mean([x["leaked"]["n"] for x in L]))
        cn = int(np.mean([x["clean"]["n"] for x in L]))
        strat[arch] = dict(leaked_n=ln, clean_n=cn,
                           leaked_acc=float(la.mean()), clean_acc=float(ca.mean()),
                           gap_pp=float((la.mean() - ca.mean()) * 100))
        print(f"  {arch:14s} leaked(n~{ln}) {la.mean():.4f}  vs  clean(n~{cn}) {ca.mean():.4f}"
              f"   gap {(la.mean()-ca.mean())*100:+.2f} pp")
    summary["within_run_leakage"] = strat

    # ---------------- shortcut probe ------------------------------------------
    print("\n" + "=" * 100)
    print("SHORTCUT PROBE (grouped split; which image content predicts the label?)")
    probe = {}
    for nod in (False, True):
        if nod:
            print("  --- control: the 429 DICOM-rendered duplicates removed ---")
        for arch in sorted({k[0] for k in runs}):
            for st in ("full", "brain", "nonbrain", "exterior"):
                k = (arch, "grouped", st, False, nod)
                if k not in runs:
                    continue
                rs = runs[k]
                a = np.array([r["test"]["accuracy"] for r in rs])
                f1 = np.array([r["test"]["macro_f1"] for r in rs])
                au = np.array([r["test"]["macro_auc"] for r in rs])
                probe[f"{arch}/{st}" + ("/nodcm" if nod else "")] = dict(
                    acc=float(a.mean()),
                    acc_sd=float(a.std(ddof=1)) if len(a) > 1 else 0.0,
                    f1=float(f1.mean()),
                    f1_sd=float(f1.std(ddof=1)) if len(f1) > 1 else 0.0,
                    auc=float(au.mean()),
                    auc_sd=float(au.std(ddof=1)) if len(au) > 1 else 0.0)
                print(f"  {arch:12s} {st:9s} acc {a.mean():.4f}  macroF1 {f1.mean():.4f}  "
                      f"macroAUC {au.mean():.4f}   (n={len(rs)})")
    summary["shortcut_probe"] = probe

    # majority-class and chance references
    import csv
    rows = list(csv.DictReader(open(os.path.join(DATA, "manifest_raw.csv"), encoding="utf-8")))
    lab = np.array([int(r["label"]) for r in rows])
    summary["reference"] = dict(majority_class_accuracy=float(np.bincount(lab).max()/len(lab)),
                                chance_macro_f1=1/3, chance_auc=0.5,
                                class_counts=np.bincount(lab).tolist())
    print(f"\n  reference: majority-class accuracy = {summary['reference']['majority_class_accuracy']:.4f}"
          f"   (class counts {summary['reference']['class_counts']})")

    # ---------------- bootstrap CIs on the headline runs -----------------------
    print("\nBOOTSTRAP 95% CIs (pooled seeds, headline configurations)")
    ci = {}
    for arch, policy in itertools.product(["densenet201", "resnet18", "resnet50"],
                                          ["grouped", "random"]):
        fs = sorted(glob.glob(os.path.join(RUNS, f"{arch}_{policy}_full_s*_preds.npz")))
        fs = [f for f in fs if "perm" not in f and "nodcm" not in f]
        if not fs: continue
        P = np.concatenate([np.load(f)["P"] for f in fs])
        Y = np.concatenate([np.load(f)["Y"] for f in fs])
        c = dict(accuracy=[acc(P, Y), *boot_ci(P, Y, acc)],
                 macro_f1=[macro_f1(P, Y), *boot_ci(P, Y, macro_f1)],
                 macro_auc=[macro_auc(P, Y), *boot_ci(P, Y, macro_auc)])
        ci[f"{arch}/{policy}"] = c
        print(f"  {arch:12s} {policy:8s} acc {c['accuracy'][0]:.4f} "
              f"[{c['accuracy'][1]:.4f},{c['accuracy'][2]:.4f}]  "
              f"F1 {c['macro_f1'][0]:.4f} [{c['macro_f1'][1]:.4f},{c['macro_f1'][2]:.4f}]  "
              f"AUC {c['macro_auc'][0]:.4f} [{c['macro_auc'][1]:.4f},{c['macro_auc'][2]:.4f}]")
    summary["bootstrap_ci"] = ci

    json.dump(summary, open(os.path.join(RES, "summary.json"), "w"), indent=2)
    print("\nsaved _results/summary.json")


if __name__ == "__main__":
    main()
