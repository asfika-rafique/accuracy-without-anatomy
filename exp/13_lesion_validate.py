# -*- coding: utf-8 -*-
"""Validate the linchpin assumption of the content ablation, and measure
attribution against the annotated lesion rather than against the whole brain.

The ablation argument rests on one claim: the "non-brain" stream contains no
lesion. That claim is geometric, not annotated -- so we test it against the
expert stroke masks distributed with a mask-bearing mirror of the same
collection (matched by the original release filename).

  (1) fraction of annotated lesion pixels lying inside our intracranial mask
  (2) fraction lying inside the head mask
  (3) Grad-CAM mass inside the annotated lesion vs the lesion's area share
"""
import os, csv, json, glob, re
import numpy as np
import torch, torch.nn as nn
import torch.nn.functional as F
from torchvision import models
from PIL import Image

import sys, os as _os
sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _config import ROOT, DATA, RESULTS, RUNS, LESION_MASKS

ROOT = ROOT; DATA = DATA
RES = RESULTS; RUNS = os.path.join(RES, "runs")
LM = LESION_MASKS
DEV = "cuda" if torch.cuda.is_available() else "cpu"
MEAN = torch.tensor([0.485, 0.456, 0.406]).view(3, 1, 1)
STD = torch.tensor([0.229, 0.224, 0.225]).view(3, 1, 1)

CIMG = np.load(os.path.join(DATA, "cache_img_256.npy"), mmap_mode="r")
CMB = np.load(os.path.join(DATA, "cache_mb_256.npy"), mmap_mode="r")
CMH = np.load(os.path.join(DATA, "cache_mh_256.npy"), mmap_mode="r")

# ---- index the downloaded lesion masks by original numeric ID --------------
lesion = {}
for f in glob.glob(os.path.join(LM, "*", "masks", "*.png")):
    if ".cache" in f:
        continue
    b = os.path.splitext(os.path.basename(f))[0]
    if b.isdigit():
        lesion[int(b)] = f
print("lesion masks indexed:", len(lesion))

rows = list(csv.DictReader(open(os.path.join(DATA, "manifest_raw.csv"), encoding="utf-8")))
byid = {}
for r in rows:
    b = os.path.splitext(r["orig"])[0]
    if b.isdigit():
        byid[int(b)] = r
match = sorted(set(lesion) & set(byid))
print("matched to our manifest:", len(match))
if not match:
    raise SystemExit("no overlap -- the mirror is not the same collection")

# ---- (1)(2) containment ----------------------------------------------------
inside_brain, inside_head, areas, cls = [], [], [], []
for k in match:
    r = byid[k]; j = int(r["idx"])
    m = np.array(Image.open(lesion[k]).convert("L").resize((256, 256), Image.NEAREST)) > 127
    if m.sum() < 20:
        continue
    mb = np.asarray(CMB[j]) > 0
    mh = np.asarray(CMH[j]) > 0
    inside_brain.append(float((m & mb).sum() / m.sum()))
    inside_head.append(float((m & mh).sum() / m.sum()))
    areas.append(float(m.mean())); cls.append(r["cls"])

ib, ih, ar = np.array(inside_brain), np.array(inside_head), np.array(areas)
print(f"\nLESION CONTAINMENT  (n = {len(ib)} annotated slices)")
print(f"  inside intracranial mask: mean {ib.mean():.4f}  median {np.median(ib):.4f}  "
      f"p10 {np.percentile(ib,10):.4f}   >=0.90 for {float((ib>=0.90).mean()):.3f} of slices")
print(f"  inside head mask        : mean {ih.mean():.4f}  median {np.median(ih):.4f}")
print(f"  lesion area share       : mean {ar.mean():.4f}  median {np.median(ar):.4f}")
out = dict(n=len(ib),
           lesion_inside_brainmask=dict(mean=float(ib.mean()), median=float(np.median(ib)),
                                        p10=float(np.percentile(ib, 10)),
                                        frac_ge_090=float((ib >= 0.90).mean())),
           lesion_inside_headmask=dict(mean=float(ih.mean()), median=float(np.median(ih))),
           lesion_area_share=dict(mean=float(ar.mean()), median=float(np.median(ar))))

# ---- (3) Grad-CAM inside the annotated lesion ------------------------------
m18 = models.resnet18(weights=None); m18.fc = nn.Linear(m18.fc.in_features, 3)
ck = os.path.join(RUNS, "resnet18_grouped_full_s0.pt")
m18.load_state_dict(torch.load(ck, map_location="cpu")); m18.eval().to(DEV)
acts, grads = {}, {}
def fwd(_, __, o):
    acts["a"] = o; o.register_hook(lambda g: grads.__setitem__("g", g))
m18.layer4.register_forward_hook(fwd)

split = list(csv.DictReader(open(os.path.join(RES, "split_grouped_s0.csv"))))
testidx = {int(r["idx"]) for r in split if r["part"] == "test"}

e_in, a_in = [], []
for k in match:
    r = byid[k]; j = int(r["idx"])
    if j not in testidx:
        continue
    m = np.array(Image.open(lesion[k]).convert("L").resize((256, 256), Image.NEAREST)) > 127
    if m.sum() < 20:
        continue
    g = np.asarray(CIMG[j]).copy()
    x = torch.from_numpy(g).float().div_(255.).unsqueeze(0).repeat(3, 1, 1)
    x = F.interpolate(x[None], size=(224, 224), mode="bilinear", align_corners=False)[0]
    x = ((x - MEAN) / STD)[None].to(DEV)
    out_ = m18(x); c = int(out_.argmax(1))
    m18.zero_grad(set_to_none=True); out_[0, c].backward()
    A, G = acts["a"], grads["g"]
    cam = F.relu((G.mean((2, 3), keepdim=True) * A).sum(1, keepdim=True))
    cam = F.interpolate(cam, size=(256, 256), mode="bilinear", align_corners=False)[0, 0]
    cam = cam.detach().cpu().numpy()
    if cam.sum() <= 0:
        continue
    cam = cam / cam.sum()
    e_in.append(float(cam[m].sum())); a_in.append(float(m.mean()))

if e_in:
    e_in, a_in = np.array(e_in), np.array(a_in)
    print(f"\nATTRIBUTION vs ANNOTATED LESION  (n = {len(e_in)} annotated test slices)")
    print(f"  Grad-CAM mass inside lesion : mean {e_in.mean():.4f}  median {np.median(e_in):.4f}")
    print(f"  lesion area share (null)    : mean {a_in.mean():.4f}")
    print(f"  enrichment (mass / area)    : {e_in.mean()/a_in.mean():.3f}x")
    out["attribution_vs_lesion"] = dict(n=int(len(e_in)),
                                        cam_mass_in_lesion=float(e_in.mean()),
                                        lesion_area_share=float(a_in.mean()),
                                        enrichment=float(e_in.mean() / a_in.mean()))

json.dump(out, open(os.path.join(RES, "lesion_validation.json"), "w"), indent=2)
print("\nsaved lesion_validation.json")
