# -*- coding: utf-8 -*-
"""Redundancy / near-duplicate audit of the TEKNO21 public PNG release.

Two independent redundancy signals are available and both are measured here.

(1) PROVENANCE DUPLICATES.  429 images in the release are named
    "{class}_dcm_{ID}.png" and every one of those IDs also occurs as a plain
    "{ID}.png".  These are the same scan stored twice.  They give us 429
    GROUND-TRUTH same-scan pairs, which we use to calibrate the detector.

(2) PERCEPTUAL NEAR-DUPLICATES.  A 256-bit dHash signature per image, with
    connected components of the near-duplicate graph forming groups.

Because the release carries no subject identifiers, these groups are a strict
LOWER BOUND on true examination-level grouping: every grouped pair is genuinely
near-identical, but same-patient slices that differ more will be missed.  Any
accuracy drop measured against a redundancy-aware split is therefore a lower
bound on the drop a true patient-level split would produce.
"""
import os, csv, json, re
import numpy as np
from PIL import Image

import sys, os as _os
sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _config import ROOT, DATA, RESULTS

DATA = DATA
IMG  = os.path.join(DATA, "images")
RES  = RESULTS
os.makedirs(RES, exist_ok=True)

SIDE = 16                       # dHash -> 16*16 = 256 bits
THRESHOLDS = [0, 2, 4, 6, 8, 10, 12, 16, 20, 24, 32]


def dhash_bits(path, side=SIDE):
    im = Image.open(path).convert("L").resize((side + 1, side), Image.LANCZOS)
    a = np.asarray(im, dtype=np.int16)
    return (a[:, 1:] > a[:, :-1]).ravel()


def hamming_block(packed, POP, s, e):
    blk = packed[s:e]
    x = np.bitwise_xor(blk[:, None, :], packed[None, :, :])
    return POP[x].sum(axis=2, dtype=np.int16)


def main():
    rows = list(csv.DictReader(open(os.path.join(DATA, "manifest_raw.csv"), encoding="utf-8")))
    n = len(rows)
    files = [r["file"] for r in rows]
    print("images:", n)

    sig_path = os.path.join(RES, "dhash_bits.npy")
    if os.path.exists(sig_path):
        bits = np.load(sig_path)
    else:
        print("computing dHash signatures ...")
        bits = np.zeros((n, SIDE * SIDE), dtype=bool)
        for i, f in enumerate(files):
            bits[i] = dhash_bits(os.path.join(IMG, f))
            if (i + 1) % 1500 == 0:
                print("  ", i + 1)
        np.save(sig_path, bits)

    packed = np.packbits(bits, axis=1)
    POP = np.unpackbits(np.arange(256, dtype=np.uint8)[:, None], axis=1).sum(1).astype(np.int16)

    # ---- ground-truth same-scan pairs from the provenance duplication --------
    num, oth = {}, {}
    for i, r in enumerate(rows):
        b = os.path.splitext(r["orig"])[0]
        if b.isdigit():
            num[int(b)] = i
        else:
            m = re.search(r"(\d+)$", b)
            if m:
                oth[int(m.group(1))] = i
    gt_pairs = [(num[k], oth[k]) for k in sorted(set(num) & set(oth))]
    print("ground-truth same-scan pairs:", len(gt_pairs))

    gt_d = np.array([int(POP[np.bitwise_xor(packed[a], packed[b])].sum())
                     for a, b in gt_pairs])
    rng = np.random.default_rng(0)
    ra, rb = rng.integers(0, n, 200000), rng.integers(0, n, 200000)
    keep = ra != rb
    rnd_d = np.array([int(POP[np.bitwise_xor(packed[a], packed[b])].sum())
                      for a, b in zip(ra[keep][:20000], rb[keep][:20000])])

    calib = dict(
        gt_pairs=len(gt_pairs),
        gt_hamming=dict(min=int(gt_d.min()), p50=float(np.median(gt_d)),
                        p90=float(np.percentile(gt_d, 90)),
                        p99=float(np.percentile(gt_d, 99)), max=int(gt_d.max()),
                        mean=float(gt_d.mean())),
        random_hamming=dict(p1=float(np.percentile(rnd_d, 1)),
                            p5=float(np.percentile(rnd_d, 5)),
                            p50=float(np.median(rnd_d)), mean=float(rnd_d.mean())),
    )
    print(json.dumps(calib, indent=2))

    # ---- full near-duplicate graph ------------------------------------------
    maxT = max(THRESHOLDS)
    pair_list = []
    B = 256
    print("pairwise hamming ...")
    for s in range(0, n, B):
        d = hamming_block(packed, POP, s, min(s + B, n))
        bi, bj = np.where(d <= maxT)
        for il, j in zip(bi, bj):
            i = s + il
            if j > i:
                pair_list.append((i, j, int(d[il, j])))
        if (s // B) % 8 == 0:
            print("   ", s, "/", n, " pairs so far:", len(pair_list))
    print("pairs <= %d:" % maxT, len(pair_list))

    stats = {}
    for t in THRESHOLDS:
        parent = list(range(n))

        def find(a):
            while parent[a] != a:
                parent[a] = parent[parent[a]]; a = parent[a]
            return a

        for i, j, dd in pair_list:
            if dd <= t:
                ra_, rb_ = find(i), find(j)
                if ra_ != rb_:
                    parent[rb_] = ra_
        comp = {}
        for i in range(n):
            comp.setdefault(find(i), []).append(i)
        sizes = np.array([len(v) for v in comp.values()])
        # recall on the ground-truth pairs at this threshold
        gid = {}
        for k, (_, mem) in enumerate(sorted(comp.items())):
            for m in mem:
                gid[m] = k
        gt_rec = float(np.mean([gid[a] == gid[b] for a, b in gt_pairs]))
        stats[t] = dict(threshold=t,
                        n_pairs=int(sum(1 for _, _, dd in pair_list if dd <= t)),
                        n_groups=int(len(comp)),
                        images_in_multi_groups=int(sizes[sizes > 1].sum()),
                        frac_in_multi_groups=float(sizes[sizes > 1].sum() / n),
                        max_group=int(sizes.max()),
                        mean_group=float(sizes.mean()),
                        gt_pair_recall=gt_rec)
        print(t, stats[t])
        with open(os.path.join(RES, f"groups_t{t}.csv"), "w", newline="") as fh:
            w = csv.writer(fh); w.writerow(["idx", "file", "orig", "cls", "group"])
            for i in range(n):
                w.writerow([i, rows[i]["file"], rows[i]["orig"], rows[i]["cls"], gid[i]])

    json.dump(dict(n_images=n, signature="dhash-256", calibration=calib, stats=stats),
              open(os.path.join(RES, "dup_stats.json"), "w"), indent=2)
    print("saved dup_stats.json")


if __name__ == "__main__":
    main()
