# -*- coding: utf-8 -*-
"""Decode the TEKNO21 parquet release into PNGs + a manifest that preserves the
ORIGINAL release filenames (they survive inside the parquet `image.path` field).

Class names from the release metadata:
    0 = "Kanama"    (haemorrhagic)
    1 = "iskemi"    (ischaemic)
    2 = "Inme Yok"  (no stroke / normal)
"""
import os, io, csv, json
from collections import Counter
import pyarrow.parquet as pq
from PIL import Image

import sys, os as _os
sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _config import ROOT, DATA

DATA = DATA
IMG  = os.path.join(DATA, "images")
os.makedirs(IMG, exist_ok=True)

CLASS_NAMES = {0: "hemorrhagic", 1: "ischemic", 2: "normal"}

rows, n = [], 0
for f in sorted(x for x in os.listdir(DATA) if x.endswith(".parquet")):
    pf = pq.ParquetFile(os.path.join(DATA, f))
    print(f, "row groups:", pf.num_row_groups, "rows:", pf.metadata.num_rows)
    for rg in range(pf.num_row_groups):
        d = pf.read_row_group(rg).to_pydict()
        for rec, lab in zip(d["image"], d["label"]):
            raw, src = rec["bytes"], rec.get("path")
            im = Image.open(io.BytesIO(raw))
            g = im.convert("L")
            out = f"{n:05d}.png"
            g.save(os.path.join(IMG, out))
            rows.append(dict(idx=n, file=out, orig=src, label=int(lab),
                             cls=CLASS_NAMES[int(lab)], w=im.width, h=im.height,
                             mode=im.mode, parquet=f))
            n += 1
        if rg % 10 == 0:
            print("   rg", rg, "->", n)

with open(os.path.join(DATA, "manifest_raw.csv"), "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
    w.writeheader(); w.writerows(rows)

print("\nTOTAL:", n)
print("classes:", Counter(r["cls"] for r in rows))
print("sizes  :", Counter((r["w"], r["h"]) for r in rows).most_common(8))
print("modes  :", Counter(r["mode"] for r in rows))
origs = [r["orig"] for r in rows if r["orig"]]
print("orig filenames present:", len(origs), "unique:", len(set(origs)))
nums = sorted(int(os.path.splitext(o)[0]) for o in origs if os.path.splitext(o)[0].isdigit())
if nums:
    print("orig numeric range:", nums[0], "-", nums[-1], "| count:", len(nums))
    gaps = sum(1 for a, b in zip(nums, nums[1:]) if b - a == 1)
    print("consecutive-number adjacencies:", gaps)
