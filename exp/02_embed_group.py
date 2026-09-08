# -*- coding: utf-8 -*-
"""Stronger redundancy grouping via deep embeddings, plus a test of whether the
original TEKNO21 file numbering encodes examination structure.

dHash finds near-identical images.  Same-patient *different* slices are not
near-identical, so dHash under-groups them.  An ImageNet embedding is far more
sensitive to shared anatomy, so we use it to build a second, wider grouping and
calibrate both against the 429 ground-truth same-scan pairs.
"""
import os, csv, json, re
import numpy as np
import torch, torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms, models
from PIL import Image

import sys, os as _os
sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _config import ROOT, DATA, RESULTS

DATA = DATA; IMG = os.path.join(DATA, "images")
RES  = RESULTS; os.makedirs(RES, exist_ok=True)
DEV  = "cuda" if torch.cuda.is_available() else "cpu"

rows = list(csv.DictReader(open(os.path.join(DATA, "manifest_raw.csv"), encoding="utf-8")))
n = len(rows)

TF = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
])


class DS(Dataset):
    def __len__(self): return n
    def __getitem__(self, i):
        im = Image.open(os.path.join(IMG, rows[i]["file"])).convert("RGB")
        return TF(im), i


def embeddings():
    p = os.path.join(RES, "emb_r50.npy")
    if os.path.exists(p):
        return np.load(p)
    m = models.resnet50(weights=models.ResNet50_Weights.IMAGENET1K_V2)
    m.fc = nn.Identity(); m.eval().to(DEV)
    out = np.zeros((n, 2048), dtype=np.float32)
    dl = DataLoader(DS(), batch_size=64, num_workers=0)
    with torch.no_grad():
        for x, idx in dl:
            f = m(x.to(DEV, non_blocking=True))
            out[idx.numpy()] = f.cpu().numpy()
            if idx[0].item() % 1024 == 0:
                print("  emb", idx[0].item())
    np.save(p, out)
    return out


def main():
    E = embeddings()
    E = E / (np.linalg.norm(E, axis=1, keepdims=True) + 1e-8)
    print("embeddings:", E.shape)

    # ---- ground-truth same-scan pairs ---------------------------------------
    num, oth = {}, {}
    for i, r in enumerate(rows):
        b = os.path.splitext(r["orig"])[0]
        if b.isdigit(): num[int(b)] = i
        else:
            m = re.search(r"(\d+)$", b)
            if m: oth[int(m.group(1))] = i
    gt = [(num[k], oth[k]) for k in sorted(set(num) & set(oth))]
    gt_sim = np.array([float(E[a] @ E[b]) for a, b in gt])

    rng = np.random.default_rng(0)
    ra, rb = rng.integers(0, n, 30000), rng.integers(0, n, 30000)
    keep = ra != rb
    rnd_sim = (E[ra[keep]] * E[rb[keep]]).sum(1)

    print("\nGT same-scan cosine: p1=%.4f p5=%.4f p50=%.4f min=%.4f"
          % (np.percentile(gt_sim, 1), np.percentile(gt_sim, 5),
             np.median(gt_sim), gt_sim.min()))
    print("random-pair cosine : p50=%.4f p95=%.4f p99=%.4f p99.9=%.4f max=%.4f"
          % (np.median(rnd_sim), np.percentile(rnd_sim, 95),
             np.percentile(rnd_sim, 99), np.percentile(rnd_sim, 99.9), rnd_sim.max()))

    # ---- does the original numbering encode examination structure? ----------
    ids = np.full(n, -1, dtype=np.int64)
    for i, r in enumerate(rows):
        b = os.path.splitext(r["orig"])[0]
        if b.isdigit(): ids[i] = int(b)
    have = np.where(ids >= 0)[0]
    order = have[np.argsort(ids[have])]
    gapsim = {}
    for gap in [1, 2, 3, 5, 10, 50, 500]:
        a, b = order[:-gap], order[gap:]
        idgap = ids[b] - ids[a]
        sel = idgap <= gap * 3          # keep genuinely close IDs only
        s = (E[a[sel]] * E[b[sel]]).sum(1)
        gapsim[gap] = dict(n=int(sel.sum()), mean=float(s.mean()),
                           p50=float(np.median(s)), p90=float(np.percentile(s, 90)))
        print(f"ID-gap {gap:4d}: n={sel.sum():5d} mean_cos={s.mean():.4f} "
              f"p50={np.median(s):.4f} p90={np.percentile(s,90):.4f}")
    print("random baseline mean_cos=%.4f" % rnd_sim.mean())

    # ---- embedding-based grouping at calibrated thresholds ------------------
    # threshold candidates chosen ABOVE the random-pair upper tail
    stats = {}
    for T in [0.90, 0.92, 0.94, 0.95, 0.96, 0.97, 0.98]:
        parent = list(range(n))
        def find(a):
            while parent[a] != a:
                parent[a] = parent[parent[a]]; a = parent[a]
            return a
        B = 512
        npair = 0
        for s in range(0, n, B):
            S = E[s:s+B] @ E.T
            bi, bj = np.where(S >= T)
            for il, j in zip(bi, bj):
                i = s + il
                if j > i:
                    npair += 1
                    ra_, rb_ = find(i), find(j)
                    if ra_ != rb_: parent[rb_] = ra_
        comp = {}
        for i in range(n): comp.setdefault(find(i), []).append(i)
        sizes = np.array([len(v) for v in comp.values()])
        gid = {}
        for k, (_, mem) in enumerate(sorted(comp.items())):
            for m in mem: gid[m] = k
        rec = float(np.mean([gid[a] == gid[b] for a, b in gt]))
        stats[T] = dict(threshold=T, n_pairs=npair, n_groups=int(len(comp)),
                        images_in_multi=int(sizes[sizes > 1].sum()),
                        frac_in_multi=float(sizes[sizes > 1].sum()/n),
                        max_group=int(sizes.max()), gt_pair_recall=rec)
        print(T, stats[T])
        with open(os.path.join(RES, f"embgroups_{int(T*100)}.csv"), "w", newline="") as fh:
            w = csv.writer(fh); w.writerow(["idx", "file", "orig", "cls", "group"])
            for i in range(n):
                w.writerow([i, rows[i]["file"], rows[i]["orig"], rows[i]["cls"], gid[i]])

    json.dump(dict(gt_cos=dict(p1=float(np.percentile(gt_sim,1)), min=float(gt_sim.min()),
                               p50=float(np.median(gt_sim))),
                   rnd_cos=dict(p50=float(np.median(rnd_sim)),
                                p99=float(np.percentile(rnd_sim,99)),
                                p999=float(np.percentile(rnd_sim,99.9)),
                                max=float(rnd_sim.max())),
                   id_gap_similarity=gapsim, emb_groups=stats),
              open(os.path.join(RES, "emb_group_stats.json"), "w"), indent=2)
    print("saved emb_group_stats.json")


if __name__ == "__main__":
    main()
