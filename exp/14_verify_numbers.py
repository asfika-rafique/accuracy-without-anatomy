# -*- coding: utf-8 -*-
"""Cross-check every headline number in the rendered PDF against the result files."""
import json, re, os

import sys, os as _os
sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _config import ROOT, RESULTS

R = RESULTS
t = open(_os.path.join(ROOT, "_full.txt"), encoding="utf-8").read()
t = re.sub(r"\s+", " ", t)

summ = json.load(open(os.path.join(R, "summary.json")))
stats = json.load(open(os.path.join(R, "stats.json")))
cross = json.load(open(os.path.join(R, "crossstream.json")))
perc = json.load(open(os.path.join(R, "perclass.json")))
lesv = json.load(open(os.path.join(R, "lesion_validation.json")))
dup = json.load(open(os.path.join(R, "dup_stats.json")))

checks = []


def ck(label, value, fmt="%.4f"):
    txt = fmt % value if isinstance(value, float) else str(value)
    checks.append((label, txt, txt in t))


P = summ["shortcut_probe"]
ck("resnet18 grouped full acc", P["resnet18/full"]["acc"])
ck("resnet18 grouped brain acc", P["resnet18/brain"]["acc"])
ck("resnet18 grouped nonbrain acc", P["resnet18/nonbrain"]["acc"])
ck("resnet18 grouped exterior acc", P["resnet18/exterior"]["acc"])
ck("exterior macro-AUC", P["resnet18/exterior"]["auc"])
ck("densenet grouped acc", P["densenet201/full"]["acc"])
ck("resnet50 grouped acc", P["resnet50/full"]["acc"])
ck("nodcm full acc", P["resnet18/full/nodcm"]["acc"])
ck("nodcm nonbrain acc", P["resnet18/nonbrain/nodcm"]["acc"])
ck("nodcm exterior acc", P["resnet18/exterior/nodcm"]["acc"])

L = summ["within_run_leakage"]
ck("densenet leaked acc", L["densenet201"]["leaked_acc"])
ck("densenet clean acc", L["densenet201"]["clean_acc"])
ck("resnet18 leaked acc", L["resnet18"]["leaked_acc"])
ck("resnet18 clean acc", L["resnet18"]["clean_acc"])

S = stats
ck("full-brain delta", abs(S["full_vs_brain_acc"]["delta"]))
ck("brain-nonbrain delta", abs(S["brain_vs_nonbrain_acc"]["delta"]))
ck("full-nonbrain delta", abs(S["full_vs_nonbrain_acc"]["delta"]))
ck("nonbrain-exterior delta", abs(S["nonbrain_vs_exterior_acc"]["delta"]))
ck("exterior AUC boot mean", S["exterior_macro_auc"]["mean"])
sen = S["sensitivity_reliable_mask"]
for k in ("full", "brain", "nonbrain", "exterior"):
    ck("sensitivity " + k, sen[k]["acc"])

for k in ("full", "brain", "nonbrain", "exterior"):
    ck("crossstream " + k + " acc", cross[k]["acc"])
    ck("crossstream " + k + " auc", cross[k]["auc"])

A = perc["full_vs_nonbrain_agreement"]
ck("agreement", A["agreement"] * 100, "%.1f")
ck("both correct", A["both_correct"] * 100, "%.1f")

ck("lesion inside brainmask", lesv["lesion_inside_brainmask"]["mean"] * 100, "%.1f")
ck("redundancy frac", dup["stats"]["6"]["frac_in_multi_groups"] * 100, "%.1f")

# multi-seed attribution + permuted control (added in the final audit)
att = json.load(open(os.path.join(R, "attrib_multiseed.json")))["summary"]
ck("attribution enrichment (3 seeds)", att["enrichment_mean"], "%.2f")
ck("CAM mass in lesion", att["cam_in_lesion_mean"] * 100, "%.2f")
ck("CAM mass outside brain", att["cam_outside_brain_mean"] * 100, "%.1f")
perm = summ.get("resnet18/grouped/full/True/False")
if perm:
    ck("permuted accuracy", perm["accuracy_mean"])
    ck("permuted macro-AUC", perm["macro_auc_mean"])

bad = [c for c in checks if not c[2]]
for lab, txt, ok in checks:
    print(("  OK   " if ok else "  MISS ") + f"{lab:34s} {txt}")
print(f"\n{len(checks)-len(bad)}/{len(checks)} numbers verified against result files")
if bad:
    print("NOT FOUND IN MANUSCRIPT:")
    for lab, txt, _ in bad:
        print("   ", lab, "=", txt)
