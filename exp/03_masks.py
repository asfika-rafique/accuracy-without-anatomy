# -*- coding: utf-8 -*-
"""Precompute intracranial ("brain") masks for the shortcut-probe experiment.

Purpose: build two counterfactual input streams from every slice.
  brain     : intracranial contents only (skull, scalp, air, scanner table removed)
  nonbrain  : the exact complement (skull/scalp/table kept, brain removed)

If a classifier trained on `nonbrain` still separates the three diagnostic
classes well above chance, the label is predictable from content that cannot
contain the lesion -- direct evidence of a non-pathological shortcut.
"""
import os, csv
import numpy as np
import cv2
from PIL import Image

import sys, os as _os
sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _config import ROOT, DATA, RESULTS

DATA = DATA; IMG = os.path.join(DATA, "images")
MB   = os.path.join(DATA, "mask_brain"); os.makedirs(MB, exist_ok=True)
MH   = os.path.join(DATA, "mask_head");  os.makedirs(MH, exist_ok=True)

AIR_T   = 15     # anything at/below this is air/background
SKULL_T = 150    # bright bone / scanner table


def head_mask(g):
    """Largest connected bright-ish component = patient head. Everything OUTSIDE
    it is scanner table / headrest / background and cannot contain a lesion."""
    head = (g > AIR_T).astype(np.uint8)
    head = cv2.morphologyEx(head, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    nlab, lab, stats, _ = cv2.connectedComponentsWithStats(head, 8)
    if nlab <= 1:
        return np.zeros_like(g)
    k = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    m = (lab == k).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
    m = cv2.dilate(m, np.ones((5, 5), np.uint8))
    return (m * 255).astype(np.uint8)


def brain_mask(g):
    """g: uint8 grayscale slice -> uint8 {0,255} intracranial mask.

    Geometric definition: the intracranial compartment is the region ENCLOSED by
    the bright skull ring.  This is deliberate -- an intensity-based definition
    would push hyperdense acute blood into the "non-brain" stream and destroy the
    interpretation of the shortcut probe.  Filling the ring keeps blood inside.
    """
    head = (g > AIR_T).astype(np.uint8)
    head = cv2.morphologyEx(head, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    nlab, lab, stats, _ = cv2.connectedComponentsWithStats(head, 8)
    if nlab <= 1:
        return np.zeros_like(g)
    k = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    head = (lab == k).astype(np.uint8)

    # bright bone, sealed into a closed ring
    skull = (((g > SKULL_T).astype(np.uint8)) & head)
    skull = cv2.morphologyEx(skull, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    skull = cv2.dilate(skull, np.ones((3, 3), np.uint8))

    # regions enclosed by the ring = complement of skull, minus the part
    # reachable from the image border
    free = (1 - skull).astype(np.uint8)
    ff = free.copy()
    h, w = g.shape
    cv2.floodFill(ff, np.zeros((h + 2, w + 2), np.uint8), (0, 0), 0)
    for seed in ((w - 1, 0), (0, h - 1), (w - 1, h - 1)):
        cv2.floodFill(ff, np.zeros((h + 2, w + 2), np.uint8), seed, 0)
    enclosed = ff.astype(np.uint8)

    nlab, lab, stats, _ = cv2.connectedComponentsWithStats(enclosed, 8)
    if nlab <= 1:
        return np.zeros_like(g)
    k = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    m = (lab == k).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((11, 11), np.uint8))
    return (m * 255).astype(np.uint8)


def main():
    rows = list(csv.DictReader(open(os.path.join(DATA, "manifest_raw.csv"), encoding="utf-8")))
    fracs = []
    for i, r in enumerate(rows):
        g = np.array(Image.open(os.path.join(IMG, r["file"])).convert("L"))
        m = brain_mask(g)
        Image.fromarray(m).save(os.path.join(MB, r["file"]))
        hm = head_mask(g)
        Image.fromarray(hm).save(os.path.join(MH, r["file"]))
        fracs.append(float((m > 0).mean()))
        if (i + 1) % 1000 == 0:
            print("  ", i + 1)
    fracs = np.array(fracs)
    print("brain-area fraction: mean=%.4f p5=%.4f p50=%.4f p95=%.4f | empty=%d"
          % (fracs.mean(), np.percentile(fracs, 5), np.median(fracs),
             np.percentile(fracs, 95), int((fracs < 0.01).sum())))
    np.save(os.path.join(RESULTS, "brain_frac.npy"), fracs)

    # contact sheet for visual verification
    sel = [0, 1, 2, 1500, 3000, 4500, 6000, 7000]
    tiles = []
    for i in sel:
        g = np.array(Image.open(os.path.join(IMG, rows[i]["file"])).convert("L").resize((160, 160)))
        m = np.array(Image.open(os.path.join(MB, rows[i]["file"])).resize((160, 160)))
        hm = np.array(Image.open(os.path.join(MH, rows[i]["file"])).resize((160, 160)))
        b  = np.where(m > 0, g, 0)
        nb = np.where((m == 0) & (hm > 0), g, 0)
        ex = np.where(hm > 0, 0, g)
        tiles.append(np.concatenate([g, b, nb, ex], axis=0))
    sheet = np.concatenate(tiles, axis=1)
    Image.fromarray(sheet).save(os.path.join(RESULTS, "mask_check.png"))
    print("wrote mask_check.png")


if __name__ == "__main__":
    main()
