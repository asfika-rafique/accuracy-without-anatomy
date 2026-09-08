# -*- coding: utf-8 -*-
"""Cross-stream inference: does the full-slice model DEPEND on extracranial
content at test time?

Take the models trained on complete slices and, without any retraining, evaluate
them on inputs from which anatomy has been deleted. A model reasoning from the
lesion should be largely unaffected by deleting the skull and the scanner table;
a model relying on extracranial content should degrade sharply.
"""
import os, csv, json, glob
import numpy as np
import torch, torch.nn as nn
import torch.nn.functional as F
from torchvision import models
from sklearn.metrics import roc_auc_score

import sys, os as _os
sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _config import ROOT, DATA, RESULTS, RUNS

ROOT = ROOT; DATA = DATA
RES = RESULTS; RUNS = os.path.join(RES, "runs")
DEV = "cuda" if torch.cuda.is_available() else "cpu"
MEAN = torch.tensor([0.485, 0.456, 0.406]).view(3, 1, 1)
STD = torch.tensor([0.229, 0.224, 0.225]).view(3, 1, 1)
CIMG = np.load(os.path.join(DATA, "cache_img_256.npy"), mmap_mode="r")
CMB = np.load(os.path.join(DATA, "cache_mb_256.npy"), mmap_mode="r")
CMH = np.load(os.path.join(DATA, "cache_mh_256.npy"), mmap_mode="r")


def batch(idx, stream):
    xs = []
    for j in idx:
        g = np.asarray(CIMG[j]).copy()
        if stream != "full":
            mb = np.asarray(CMB[j]) > 0
            mh = np.asarray(CMH[j]) > 0
            if stream == "brain":      g = np.where(mb, g, 0)
            elif stream == "nonbrain": g = np.where(~mb & mh, g, 0)
            elif stream == "exterior": g = np.where(~mh, g, 0)
        t = torch.from_numpy(g).float().div_(255.).unsqueeze(0).repeat(3, 1, 1)
        t = F.interpolate(t[None], size=(224, 224), mode="bilinear", align_corners=False)[0]
        xs.append((t - MEAN) / STD)
    return torch.stack(xs)


def macro_auc(P, Y):
    a = []
    for c in range(3):
        yb = (Y == c).astype(int)
        if yb.min() != yb.max():
            a.append(roc_auc_score(yb, P[:, c]))
    return float(np.mean(a))


res = {}
for stream in ("full", "brain", "nonbrain", "exterior"):
    accs, aucs = [], []
    for seed in (0, 1, 2):
        ck = os.path.join(RUNS, f"resnet18_grouped_full_s{seed}.pt")
        if not os.path.exists(ck):
            print("missing checkpoint", ck); continue
        m = models.resnet18(weights=None); m.fc = nn.Linear(m.fc.in_features, 3)
        m.load_state_dict(torch.load(ck, map_location="cpu")); m.eval().to(DEV)
        rows = list(csv.DictReader(open(os.path.join(RES, f"split_grouped_s{seed}.csv"))))
        test = [r for r in rows if r["part"] == "test"]
        I = np.array([int(r["idx"]) for r in test]); Y = np.array([int(r["label"]) for r in test])
        P = []
        with torch.no_grad():
            for k in range(0, len(I), 64):
                x = batch(I[k:k + 64], stream).to(DEV)
                P.append(m(x).softmax(1).cpu().numpy())
        P = np.concatenate(P)
        accs.append(float((P.argmax(1) == Y).mean())); aucs.append(macro_auc(P, Y))
        del m; torch.cuda.empty_cache()
    if accs:
        res[stream] = dict(acc=float(np.mean(accs)), acc_sd=float(np.std(accs, ddof=1)),
                           auc=float(np.mean(aucs)), auc_sd=float(np.std(aucs, ddof=1)),
                           seeds=len(accs))
        print(f"full-slice model  ->  {stream:9s} input:  acc {np.mean(accs):.4f} "
              f"+-{np.std(accs, ddof=1):.4f}   macro-AUC {np.mean(aucs):.4f}")

json.dump(res, open(os.path.join(RES, "crossstream.json"), "w"), indent=2)
print("\nsaved crossstream.json")
