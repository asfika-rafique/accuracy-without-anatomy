# -*- coding: utf-8 -*-
"""Quantitative attribution analysis.

The historical study inspected Grad-CAM maps qualitatively. Here we measure
them: what fraction of Grad-CAM energy falls OUTSIDE the intracranial
compartment, and how does that compare with the fraction expected if attribution
were spread uniformly over the image?

  E_out = sum(CAM * (1 - brain_mask)) / sum(CAM)
  A_out = fraction of image area outside the brain mask   (uniform-attribution null)

E_out substantially above A_out would mean attribution avoids the brain; E_out
near A_out means attribution is no more brain-directed than chance. Reported for
the full-slice model trained under the redundancy-aware protocol.
"""
import os, csv, json
import numpy as np
import torch, torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader
from torchvision import models
import sys

import sys, os as _os
sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _config import ROOT, DATA, RESULTS, RUNS
sys.path.insert(0, os.path.dirname(__file__))

ROOT = ROOT; DATA = DATA
RES = RESULTS; RUNS = os.path.join(RES, "runs")
DEV = "cuda" if torch.cuda.is_available() else "cpu"
MEAN, STD = [0.485, 0.456, 0.406], [0.229, 0.224, 0.225]

CIMG = np.load(os.path.join(DATA, "cache_img_256.npy"), mmap_mode="r")
CMB = np.load(os.path.join(DATA, "cache_mb_256.npy"), mmap_mode="r")

SEED, ARCH, POLICY = 0, "resnet18", "grouped"


def main():
    rows = list(csv.DictReader(open(os.path.join(RES, f"split_{POLICY}_s{SEED}.csv"))))
    test = [r for r in rows if r["part"] == "test"]
    print("test images:", len(test))

    # rebuild and reload the selected model
    m = models.resnet18(weights=None); m.fc = nn.Linear(m.fc.in_features, 3)
    ck = os.path.join(RUNS, f"{ARCH}_{POLICY}_full_s{SEED}.pt")
    if not os.path.exists(ck):
        print("no checkpoint saved; retraining is not attempted here.")
        print("Falling back to the ImageNet-initialised model is NOT valid -> abort.")
        return
    m.load_state_dict(torch.load(ck, map_location="cpu"))
    m.eval().to(DEV)

    acts, grads = {}, {}
    def fwd(_, __, out):
        acts["a"] = out
        out.register_hook(lambda g: grads.__setitem__("g", g))
    m.layer4.register_forward_hook(fwd)

    e_out, a_out, keep = [], [], 0
    mean = torch.tensor(MEAN).view(3, 1, 1); std = torch.tensor(STD).view(3, 1, 1)
    for r in test:
        j = int(r["idx"])
        g = np.asarray(CIMG[j]).copy(); mb = np.asarray(CMB[j]).copy() > 0
        if mb.sum() < 100:          # skull-base slices without a reliable mask
            continue
        keep += 1
        x = torch.from_numpy(g).float().div_(255.).unsqueeze(0).repeat(3, 1, 1)
        x = F.interpolate(x[None], size=(224, 224), mode="bilinear", align_corners=False)[0]
        x = ((x - mean) / std)[None].to(DEV)

        out = m(x)
        cls = int(out.argmax(1))
        m.zero_grad(set_to_none=True)
        out[0, cls].backward()
        A, G = acts["a"], grads["g"]
        alpha = G.mean(dim=(2, 3), keepdim=True)
        cam = F.relu((alpha * A).sum(1, keepdim=True))
        cam = F.interpolate(cam, size=(256, 256), mode="bilinear", align_corners=False)
        cam = cam[0, 0].detach().cpu().numpy()
        if cam.sum() <= 0:
            continue
        cam = cam / cam.sum()
        e_out.append(float(cam[~mb].sum()))
        a_out.append(float((~mb).mean()))

    e_out, a_out = np.array(e_out), np.array(a_out)
    res = dict(n_slices=int(keep), n_scored=int(len(e_out)),
               cam_energy_outside_brain=dict(mean=float(e_out.mean()),
                                             p50=float(np.median(e_out)),
                                             p25=float(np.percentile(e_out, 25)),
                                             p75=float(np.percentile(e_out, 75))),
               area_outside_brain=dict(mean=float(a_out.mean()), p50=float(np.median(a_out))),
               ratio_energy_to_area=float(e_out.mean() / a_out.mean()))
    print(json.dumps(res, indent=2))
    json.dump(res, open(os.path.join(RES, "gradcam_quant.json"), "w"), indent=2)


if __name__ == "__main__":
    main()
