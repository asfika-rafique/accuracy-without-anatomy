# -*- coding: utf-8 -*-
"""Train / evaluate one configuration under a frozen protocol.

  --policy  random | grouped        split policy
  --stream  full | brain | nonbrain | exterior
  --arch    densenet201 | resnet18 | resnet50
  --seed    int
  --epochs  int

Protocol (identical for every configuration):
  * 70/15/15 stratified train/val/test
  * model selection: best epoch by VALIDATION macro-F1
  * test partition evaluated exactly once, with the selected epoch
  * class-weighted cross-entropy, AdamW, cosine schedule, AMP
Outputs one JSON per run plus per-image test predictions.
"""
import os, csv, json, time, argparse
import numpy as np
import torch, torch.nn as nn
torch.backends.cudnn.benchmark = True
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms, models
from PIL import Image
from sklearn.metrics import f1_score, roc_auc_score, confusion_matrix, accuracy_score

import sys, os as _os
sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _config import ROOT, DATA, RESULTS, RUNS

DATA = DATA; IMG = os.path.join(DATA, "images")
MB = os.path.join(DATA, "mask_brain"); MH = os.path.join(DATA, "mask_head")
RES = RESULTS; RUNS = os.path.join(RES, "runs")
os.makedirs(RUNS, exist_ok=True)
DEV = "cuda" if torch.cuda.is_available() else "cpu"
MEAN, STD = [0.485, 0.456, 0.406], [0.229, 0.224, 0.225]


# memory-mapped 256x256 caches (see 03b_cache.py) -- removes PNG decode from the loop
_CIMG = np.load(os.path.join(DATA, "cache_img_256.npy"), mmap_mode="r")
_CMB  = np.load(os.path.join(DATA, "cache_mb_256.npy"),  mmap_mode="r")
_CMH  = np.load(os.path.join(DATA, "cache_mh_256.npy"),  mmap_mode="r")


def compose(train):
    aug = [transforms.RandomResizedCrop(224, scale=(0.85, 1.0), ratio=(0.9, 1.11),
                                        antialias=True),
           transforms.RandomHorizontalFlip(),
           transforms.RandomRotation(7)] if train else [transforms.Resize((224, 224),
                                                                          antialias=True)]
    return transforms.Compose(aug)


class DS(Dataset):
    def __init__(self, recs, stream, train):
        self.idx = np.array([int(r["idx"]) for r in recs])
        self.y = np.array([int(r["label"]) for r in recs])
        self.stream = stream
        self.geo = compose(train)
        self.norm = transforms.Normalize(MEAN, STD)

    def __len__(self): return len(self.idx)

    def __getitem__(self, i):
        j = self.idx[i]
        g = np.asarray(_CIMG[j])
        if self.stream != "full":
            mb = np.asarray(_CMB[j]) > 0
            mh = np.asarray(_CMH[j]) > 0
            if self.stream == "brain":
                g = np.where(mb, g, 0)
            elif self.stream == "nonbrain":
                g = np.where(~mb & mh, g, 0)
            elif self.stream == "exterior":
                g = np.where(~mh, g, 0)
        t = torch.from_numpy(g.copy()).unsqueeze(0)          # 1 x H x W, uint8
        t = self.geo(t).float().div_(255.).repeat(3, 1, 1)   # geometry first, then 3ch
        return self.norm(t), int(self.y[i]), int(j)


def build(arch):
    if arch == "densenet201":
        m = models.densenet201(weights=models.DenseNet201_Weights.IMAGENET1K_V1)
        m.classifier = nn.Linear(m.classifier.in_features, 3)
    elif arch == "resnet18":
        m = models.resnet18(weights=models.ResNet18_Weights.IMAGENET1K_V1)
        m.fc = nn.Linear(m.fc.in_features, 3)
    elif arch == "resnet50":
        m = models.resnet50(weights=models.ResNet50_Weights.IMAGENET1K_V2)
        m.fc = nn.Linear(m.fc.in_features, 3)
    else:
        raise ValueError(arch)
    return m


@torch.no_grad()
def evaluate(model, dl):
    model.eval()
    P, Y, I = [], [], []
    for x, y, idx in dl:
        with torch.autocast("cuda", enabled=(DEV == "cuda")):
            p = model(x.to(DEV)).float().softmax(1)
        P.append(p.cpu().numpy()); Y.append(y.numpy()); I.append(idx.numpy())
    return np.concatenate(P), np.concatenate(Y), np.concatenate(I)


def metrics(P, Y):
    pred = P.argmax(1)
    out = dict(accuracy=float(accuracy_score(Y, pred)),
               macro_f1=float(f1_score(Y, pred, average="macro")),
               confusion=confusion_matrix(Y, pred, labels=[0, 1, 2]).tolist())
    aucs = {}
    for c, name in enumerate(("hemorrhagic", "ischemic", "normal")):
        yb = (Y == c).astype(int)
        aucs[name] = float(roc_auc_score(yb, P[:, c])) if yb.min() != yb.max() else float("nan")
    out["auc"] = aucs
    out["macro_auc"] = float(np.mean([v for v in aucs.values() if v == v]))
    per = []
    for c in range(3):
        m = Y == c
        per.append(float((pred[m] == c).mean()) if m.sum() else float("nan"))
    out["per_class_accuracy"] = per
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--policy", default="grouped")
    ap.add_argument("--stream", default="full")
    ap.add_argument("--arch", default="densenet201")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--epochs", type=int, default=15)
    ap.add_argument("--bs", type=int, default=48)
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--permute_labels", action="store_true")
    ap.add_argument("--save_ckpt", action="store_true")
    ap.add_argument("--exclude_dcm", action="store_true",
                    help="drop the 429 DICOM-rendered duplicates (all stroke-class, "
                         "different rendering path) as a shortcut-artefact control")
    a = ap.parse_args()

    tag = (f"{a.arch}_{a.policy}_{a.stream}_s{a.seed}"
           + ("_perm" if a.permute_labels else "")
           + ("_nodcm" if a.exclude_dcm else ""))
    outp = os.path.join(RUNS, tag + ".json")
    if os.path.exists(outp):
        print("exists, skip:", tag); return

    torch.manual_seed(a.seed); np.random.seed(a.seed)
    rows = list(csv.DictReader(open(os.path.join(RES, f"split_{a.policy}_s{a.seed}.csv"))))
    if a.permute_labels:
        rng = np.random.default_rng(1234 + a.seed)
        labs = np.array([int(r["label"]) for r in rows]); rng.shuffle(labs)
        for r, l in zip(rows, labs): r["label"] = int(l)

    if a.exclude_dcm:
        import re as _re
        man = {int(m["idx"]): m["orig"] for m in
               csv.DictReader(open(os.path.join(DATA, "manifest_raw.csv"), encoding="utf-8"))}
        keep = lambda r: os.path.splitext(man[int(r["idx"])])[0].isdigit()
        n0 = len(rows); rows = [r for r in rows if keep(r)]
        print(f"  exclude_dcm: {n0} -> {len(rows)} images")
    parts = {p: [r for r in rows if r["part"] == p] for p in ("train", "val", "test")}
    print(tag, {k: len(v) for k, v in parts.items()})

    dl = {p: DataLoader(DS(parts[p], a.stream, p == "train"), batch_size=a.bs,
                        shuffle=(p == "train"), num_workers=4, pin_memory=True,
                        persistent_workers=True, drop_last=(p == "train"))
          for p in parts}

    ytr = np.array([int(r["label"]) for r in parts["train"]])
    cnt = np.bincount(ytr, minlength=3).astype(np.float64)
    wt = torch.tensor((cnt.sum() / (3 * np.maximum(cnt, 1))), dtype=torch.float32, device=DEV)

    model = build(a.arch).to(DEV)   # NOTE: channels_last measured 4x SLOWER for DenseNet-201
    opt = torch.optim.AdamW(model.parameters(), lr=a.lr, weight_decay=1e-4)
    sch = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=a.epochs)
    crit = nn.CrossEntropyLoss(weight=wt)
    scaler = torch.amp.GradScaler("cuda", enabled=(DEV == "cuda"))

    hist, best, best_state, t0 = [], -1.0, None, time.time()
    for ep in range(a.epochs):
        model.train(); tot = 0.0; nb = 0
        for x, y, _ in dl["train"]:
            x = x.to(DEV, non_blocking=True)
            y = y.to(DEV, non_blocking=True)
            opt.zero_grad(set_to_none=True)
            with torch.autocast("cuda", enabled=(DEV == "cuda")):
                loss = crit(model(x), y)
            scaler.scale(loss).backward(); scaler.step(opt); scaler.update()
            tot += loss.item(); nb += 1
        sch.step()
        Pv, Yv, _ = evaluate(model, dl["val"])
        mv = metrics(Pv, Yv)
        hist.append(dict(epoch=ep + 1, train_loss=tot / max(nb, 1),
                         val_acc=mv["accuracy"], val_macro_f1=mv["macro_f1"],
                         val_macro_auc=mv["macro_auc"]))
        print(f"  ep{ep+1:02d} loss {tot/max(nb,1):.4f} val_f1 {mv['macro_f1']:.4f} "
              f"val_acc {mv['accuracy']:.4f}")
        if mv["macro_f1"] > best:
            best = mv["macro_f1"]
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
            best_ep = ep + 1

    model.load_state_dict(best_state)
    Pt, Yt, It = evaluate(model, dl["test"])
    mt = metrics(Pt, Yt)

    # within-run leakage stratification: test images WITH vs WITHOUT a
    # near-duplicate in the training partition
    gtrain = {r["group"] for r in parts["train"]}
    gmap = {int(r["idx"]): r["group"] for r in rows}
    leaked = np.array([gmap[i] in gtrain for i in It])
    strat = {}
    for name, m in (("leaked", leaked), ("clean", ~leaked)):
        strat[name] = dict(n=int(m.sum()))
        if m.sum() > 10:
            strat[name].update(metrics(Pt[m], Yt[m]))

    res = dict(tag=tag, arch=a.arch, policy=a.policy, stream=a.stream, seed=a.seed,
               epochs=a.epochs, batch_size=a.bs, lr=a.lr,
               permuted_labels=bool(a.permute_labels),
               exclude_dcm=bool(a.exclude_dcm),
               n_train=len(parts["train"]), n_val=len(parts["val"]), n_test=len(parts["test"]),
               best_epoch=best_ep, best_val_macro_f1=best, history=hist,
               test=mt, test_by_leakage=strat,
               minutes=round((time.time() - t0) / 60, 2),
               device=torch.cuda.get_device_name(0) if DEV == "cuda" else "cpu",
               torch=torch.__version__)
    json.dump(res, open(outp, "w"), indent=2)
    if a.save_ckpt:
        torch.save(best_state, os.path.join(RUNS, tag + ".pt"))
    np.savez(os.path.join(RUNS, tag + "_preds.npz"), P=Pt, Y=Yt, I=It, leaked=leaked)
    print(f"  TEST acc {mt['accuracy']:.4f} macroF1 {mt['macro_f1']:.4f} "
          f"macroAUC {mt['macro_auc']:.4f}  ({res['minutes']} min)")


if __name__ == "__main__":
    main()
