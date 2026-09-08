# -*- coding: utf-8 -*-
"""Pre-resize images and masks into memory-mapped uint8 arrays.

Decoding 512x512 PNGs (image + two masks) for every sample made training
I/O-bound. Caching at 256x256 removes that cost entirely and does not change
the experiment: all networks consume 224x224 crops regardless.
"""
import os, csv
import numpy as np
from PIL import Image

import sys, os as _os
sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _config import ROOT, DATA

ROOT = ROOT; DATA = DATA
IMG = os.path.join(DATA, "images"); MB = os.path.join(DATA, "mask_brain")
MH = os.path.join(DATA, "mask_head")
S = 256

rows = list(csv.DictReader(open(os.path.join(DATA, "manifest_raw.csv"), encoding="utf-8")))
n = len(rows)
out_img = np.lib.format.open_memmap(os.path.join(DATA, f"cache_img_{S}.npy"),
                                    mode="w+", dtype=np.uint8, shape=(n, S, S))
out_mb = np.lib.format.open_memmap(os.path.join(DATA, f"cache_mb_{S}.npy"),
                                   mode="w+", dtype=np.uint8, shape=(n, S, S))
out_mh = np.lib.format.open_memmap(os.path.join(DATA, f"cache_mh_{S}.npy"),
                                   mode="w+", dtype=np.uint8, shape=(n, S, S))

for i, r in enumerate(rows):
    f = r["file"]
    out_img[i] = np.array(Image.open(os.path.join(IMG, f)).convert("L").resize((S, S), Image.BILINEAR))
    out_mb[i] = np.array(Image.open(os.path.join(MB, f)).resize((S, S), Image.NEAREST))
    out_mh[i] = np.array(Image.open(os.path.join(MH, f)).resize((S, S), Image.NEAREST))
    if (i + 1) % 1500 == 0:
        print("  ", i + 1)
out_img.flush(); out_mb.flush(); out_mh.flush()
print("cached", n, "at", S)
