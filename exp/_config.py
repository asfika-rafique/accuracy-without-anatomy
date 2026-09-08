# -*- coding: utf-8 -*-
"""Single source of truth for paths, so nothing in this repository hardcodes a
machine-specific location.

Project root resolution:
  1. the STROKE_AUDIT_ROOT environment variable, if set
  2. otherwise the parent of this file (i.e. the repository checkout)

Directory names: the public repository uses clean names (``data``, ``results``,
``figures``); the original working copy used underscore-prefixed ones. Both are
accepted, so the same scripts run unchanged in either layout.
"""
import os

ROOT = os.environ.get("STROKE_AUDIT_ROOT") or os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))


def _pick(*names):
    """Return the first existing candidate; otherwise the first name."""
    for n in names:
        p = os.path.join(ROOT, n)
        if os.path.isdir(p):
            return p
    return os.path.join(ROOT, names[0])


DATA = _pick("_data", "data")
RESULTS = _pick("_results", "results")
FIGS = _pick("_final_figs", "figures")

IMG = os.path.join(DATA, "images")
MASK_BRAIN = os.path.join(DATA, "mask_brain")
MASK_HEAD = os.path.join(DATA, "mask_head")
RUNS = os.path.join(RESULTS, "runs")
LESION_MASKS = _pick("_lesionmasks", "lesionmasks")

for _d in (DATA, RESULTS, RUNS, FIGS):
    os.makedirs(_d, exist_ok=True)
