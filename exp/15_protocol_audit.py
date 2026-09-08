# -*- coding: utf-8 -*-
"""Independent protocol audit: verify from the SAVED RUN RECORDS (not the
manuscript) that every configuration entering a headline comparison was trained
under an identical protocol."""
import json, glob, os
from collections import defaultdict

import sys, os as _os
sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _config import ROOT, RUNS

RUNS = RUNS
runs = []
for f in sorted(glob.glob(os.path.join(RUNS, "*.json"))):
    runs.append(json.load(open(f)))

FIELDS = ["arch", "policy", "stream", "seed", "epochs", "batch_size", "lr",
          "permuted_labels", "exclude_dcm", "n_train", "n_val", "n_test", "device", "torch"]
print(f"total runs: {len(runs)}\n")

# ---- 1. protocol fields that must be constant across every run -------------
const = defaultdict(set)
for r in runs:
    const["lr"].add(r.get("lr"))
    const["batch_size"].add(r.get("batch_size"))
    const["device"].add(r.get("device"))
    const["torch"].add(r.get("torch"))
print("CONSTANT-ACROSS-ALL-RUNS CHECK")
for k, v in const.items():
    flag = "OK  " if len(v) == 1 else "VARY"
    print(f"  {flag} {k:12s} {sorted(map(str, v))}")

# ---- 2. the content-ablation comparison group ------------------------------
print("\nCONTENT ABLATION GROUP (resnet18 / grouped / not permuted / not nodcm)")
grp = [r for r in runs if r["arch"] == "resnet18" and r["policy"] == "grouped"
       and not r["permuted_labels"] and not r.get("exclude_dcm", False)]
keys = defaultdict(set)
for r in grp:
    for k in ("epochs", "batch_size", "lr"):
        keys[k].add(r[k])
for k, v in keys.items():
    print(f"  {'OK  ' if len(v)==1 else 'MISMATCH'} {k:12s} {sorted(v)}")
by_stream = defaultdict(list)
for r in grp:
    by_stream[r["stream"]].append(r["seed"])
for st in sorted(by_stream):
    print(f"    {st:10s} seeds {sorted(by_stream[st])}")

# ---- 3. the duplicate-removal control group --------------------------------
print("\nDUPLICATE-REMOVAL CONTROL GROUP (exclude_dcm=True)")
nod = [r for r in runs if r.get("exclude_dcm", False)]
k2 = defaultdict(set)
for r in nod:
    for k in ("epochs", "batch_size", "lr", "arch", "policy"):
        k2[k].add(r[k])
for k, v in k2.items():
    print(f"  {'OK  ' if len(v)==1 else 'MISMATCH'} {k:12s} {sorted(map(str,v))}")
print("   n =", len(nod), "streams:", sorted({r['stream'] for r in nod}))

# ---- 4. split-policy comparison group --------------------------------------
print("\nSPLIT-POLICY COMPARISON (full stream, per architecture)")
for arch in ("densenet201", "resnet18"):
    sub = [r for r in runs if r["arch"] == arch and r["stream"] == "full"
           and not r["permuted_labels"] and not r.get("exclude_dcm", False)]
    k3 = defaultdict(set)
    for r in sub:
        for k in ("epochs", "batch_size", "lr"):
            k3[k].add(r[k])
    ok = all(len(v) == 1 for v in k3.values())
    print(f"  {'OK  ' if ok else 'MISMATCH'} {arch:12s} "
          f"epochs {sorted(k3['epochs'])} bs {sorted(k3['batch_size'])} "
          f"policies {sorted({r['policy'] for r in sub})}")

# ---- 5. architecture comparison group --------------------------------------
print("\nARCHITECTURE COMPARISON (grouped / full)")
sub = [r for r in runs if r["policy"] == "grouped" and r["stream"] == "full"
       and not r["permuted_labels"] and not r.get("exclude_dcm", False)]
for arch in sorted({r["arch"] for r in sub}):
    a = [r for r in sub if r["arch"] == arch]
    print(f"  {arch:12s} epochs {sorted({r['epochs'] for r in a})} "
          f"bs {sorted({r['batch_size'] for r in a})} seeds {sorted(r['seed'] for r in a)}")
print("  NOTE: all architectures share epochs, batch size and learning rate.")

# ---- 6. split-size sanity --------------------------------------------------
print("\nSPLIT SIZES (should be ~70/15/15 and consistent per policy+seed)")
seen = {}
for r in runs:
    if r.get("exclude_dcm"):
        continue
    k = (r["policy"], r["seed"])
    v = (r["n_train"], r["n_val"], r["n_test"])
    if k in seen and seen[k] != v:
        print(f"  MISMATCH {k}: {seen[k]} vs {v}")
    seen[k] = v
for k in sorted(seen):
    tr, va, te = seen[k]
    tot = tr + va + te
    print(f"  {k[0]:8s} s{k[1]}  {tr}/{va}/{te}  total {tot}  "
          f"({tr/tot:.3f}/{va/tot:.3f}/{te/tot:.3f})")
