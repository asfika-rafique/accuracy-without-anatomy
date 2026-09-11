# Source data (not included)

Use the same `STROKE_AUDIT_ROOT` for preparation and every later pipeline step.
In a fresh workspace use `data/` for primary shards and `lesionmasks/` for expert masks.
The original working copy uses `_data/` and `_lesionmasks/`; `_config.py` accepts either.
Do not create both variants in a new workspace, because existing underscore directories win.

1. Primary classification mirror:
   https://huggingface.co/datasets/BTX24/tekno21-brain-stroke-dataset-multi
   Put all Parquet shards directly in `data/`, then run `python exp/00_prepare.py`.
   Expected manifest: 7202 slices; class counts 1290, 1361, 4551.
2. Expert-mask mirror of the SAME collection:
   https://huggingface.co/datasets/Karrar-Alhdrawi/brain-stroke-ct-dataset
   Preserve `lesionmasks/<class>/masks/<numeric-ID>.png`.
   Hugging Face snapshot selection `allow_patterns=["*/masks/*"]` retains this structure.
   This is not an independent external validation dataset.

Conditions of use of the underlying clinical collection are set by the issuing institutions,
not by a mirror's repository licence tag. Verify them at source. No source CT images or
expert lesion masks are redistributed; manuscript figures include illustrative CT panels.
