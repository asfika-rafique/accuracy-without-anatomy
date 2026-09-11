# -*- coding: utf-8 -*-
"""Multi-seed attribution analysis.

The first attribution pass used the seed-0 checkpoint only, which a reviewer can
fairly call an n=1 measurement. All three full-slice checkpoints are retained, so
we repeat both attribution metrics on each seed and report mean +/- SD:

  (1) Grad-CAM mass inside the expert-annotated lesion, against the lesion's
      area share (the uniform-attribution null)
  (2) Grad-CAM mass falling outside the intracranial compartment, against the
      fraction expected under uniform attribution
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

DEV = "cuda" if torch.cuda.is_available() else "cpu"
MEAN = torch.tensor([0.485, 0.456, 0.406]).view(3, 1, 1)
STD = torch.tensor([0.229, 0.224, 0.225]).view(3, 1, 1)
CIMG = np.load(os.path.join(DATA, "cache_img_256.npy"), mmap_mode="r")
CMB = np.load(os.path.join(DATA, "cache_mb_256.npy"), mmap_mode="r")

rows = list(csv.DictReader(open(os.path.join(DATA, "manifest_raw.csv"), encoding="utf-8")))
byid = {}
for r in rows:
    b = os.path.splitext(r["orig"])[0]
    if b.isdigit():
        byid[int(b)] = r

lesion = {}
for f in glob.glob(os.path.join(LESION_MASKS, "*", "masks", "*.png")):
    if ".cache" in f:
        continue
    b = os.path.splitext(os.path.basename(f))[0]
    if b.isdigit():
        lesion[int(b)] = f
print("lesion masks:", len(lesion))


def cam_for(model, acts, grads, j):
    g = np.asarray(CIMG[j]).copy()
    x = torch.from_numpy(g).float().div_(255.).unsqueeze(0).repeat(3, 1, 1)
    x = F.interpolate(x[None], size=(224, 224), mode="bilinear", align_corners=False)[0]
    x = ((x - MEAN) / STD)[None].to(DEV)
    out = model(x)
    c = int(out.argmax(1))
    model.zero_grad(set_to_none=True)
    out[0, c].backward()
    A, G = acts["a"], grads["g"]
    cam = F.relu((G.mean((2, 3), keepdim=True) * A).sum(1, keepdim=True))
    cam = F.interpolate(cam, size=(256, 256), mode="bilinear", align_corners=False)[0, 0]
    cam = cam.detach().cpu().numpy()
    return cam if cam.sum() > 0 else None


missing = [os.path.join(RUNS, f"resnet18_grouped_full_s{s}.pt") for s in (0, 1, 2) if not os.path.isfile(os.path.join(RUNS, f"resnet18_grouped_full_s{s}.pt"))]
if missing:
    raise FileNotFoundError("All three checkpoints are required: " + ", ".join(missing))

res = {"per_seed": {}}
E_in, A_in, OUT_f, OUTn_f = [], [], [], []

for seed in (0, 1, 2):
    ck = os.path.join(RUNS, f"resnet18_grouped_full_s{seed}.pt")
    if not os.path.exists(ck):
        print("missing checkpoint for seed", seed); continue
    m = models.resnet18(weights=None); m.fc = nn.Linear(m.fc.in_features, 3)
    m.load_state_dict(torch.load(ck, map_location="cpu", weights_only=True))
    m.eval().to(DEV)
    acts, grads = {}, {}

    def _hook(_mod, _inp, out):
        acts["a"] = out
        out.register_hook(lambda g: grads.__setitem__("g", g))
        # must return None, or the tuple would replace the layer output

    m.layer4.register_forward_hook(_hook)

    split = list(csv.DictReader(open(os.path.join(RESULTS, f"split_grouped_s{seed}.csv"))))
    testidx = {int(r["idx"]) for r in split if r["part"] == "test"}

    e_in, a_in, out_f, outn_f = [], [], [], []
    for k in sorted(set(lesion) & set(byid)):
        j = int(byid[k]["idx"])
        if j not in testidx:
            continue
        mk = np.array(Image.open(lesion[k]).convert("L").resize((256, 256), Image.NEAREST)) > 127
        if mk.sum() < 20:
            continue
        cam = cam_for(m, acts, grads, j)
        if cam is None:
            continue
        cam = cam / cam.sum()
        e_in.append(float(cam[mk].sum())); a_in.append(float(mk.mean()))

    # attribution outside the intracranial compartment, same checkpoint
    for j in sorted(testidx):
        mb = np.asarray(CMB[j]) > 0
        if mb.sum() < 100:
            continue
        cam = cam_for(m, acts, grads, j)
        if cam is None:
            continue
        cam = cam / cam.sum()
        out_f.append(float(cam[~mb].sum())); outn_f.append(float((~mb).mean()))

    res["per_seed"][seed] = dict(
        n_lesion=len(e_in), cam_in_lesion=float(np.mean(e_in)),
        lesion_area=float(np.mean(a_in)),
        enrichment=float(np.mean(e_in) / np.mean(a_in)),
        n_brain=len(out_f), cam_outside_brain=float(np.mean(out_f)),
        area_outside_brain=float(np.mean(outn_f)),
        ratio=float(np.mean(out_f) / np.mean(outn_f)))
    print(f"seed {seed}: enrichment {res['per_seed'][seed]['enrichment']:.3f}x  "
          f"outside-brain {np.mean(out_f):.4f} (null {np.mean(outn_f):.4f})")
    E_in.append(np.mean(e_in)); A_in.append(np.mean(a_in))
    OUT_f.append(np.mean(out_f)); OUTn_f.append(np.mean(outn_f))
    del m; torch.cuda.empty_cache()

enr = np.array(E_in) / np.array(A_in)
res["summary"] = dict(
    seeds=len(E_in),
    cam_in_lesion_mean=float(np.mean(E_in)), cam_in_lesion_sd=float(np.std(E_in, ddof=1)),
    lesion_area_mean=float(np.mean(A_in)),
    enrichment_mean=float(enr.mean()), enrichment_sd=float(enr.std(ddof=1)),
    cam_outside_brain_mean=float(np.mean(OUT_f)), cam_outside_brain_sd=float(np.std(OUT_f, ddof=1)),
    area_outside_brain_mean=float(np.mean(OUTn_f)),
    ratio_mean=float((np.array(OUT_f) / np.array(OUTn_f)).mean()))
print("\nSUMMARY over %d seeds" % len(E_in))
print("  CAM mass in lesion : %.4f +- %.4f  (lesion area %.4f)"
      % (res["summary"]["cam_in_lesion_mean"], res["summary"]["cam_in_lesion_sd"],
         res["summary"]["lesion_area_mean"]))
print("  enrichment         : %.2fx +- %.2f" % (res["summary"]["enrichment_mean"],
                                                res["summary"]["enrichment_sd"]))
print("  CAM mass outside brain: %.4f +- %.4f  (uniform null %.4f, ratio %.2f)"
      % (res["summary"]["cam_outside_brain_mean"], res["summary"]["cam_outside_brain_sd"],
         res["summary"]["area_outside_brain_mean"], res["summary"]["ratio_mean"]))
json.dump(res, open(os.path.join(RESULTS, "attrib_multiseed.json"), "w"), indent=2)
print("\nsaved attrib_multiseed.json")
