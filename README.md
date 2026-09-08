# Accuracy Without Anatomy

Code and analysis for *"Accuracy Without Anatomy: A Redundancy and Shortcut Audit of a Public
Head-CT Stroke Benchmark."*

The paper asks what near-ceiling three-class stroke accuracy on a widely used public
non-contrast head-CT collection actually measures. Short answer, established by controlled
ablation: **most of it is obtainable from image content outside the brain.**

---

## What this repository contains

Every number in the manuscript is produced by the scripts in `exp/`, in the order they are
numbered. Nothing is hand-entered.

```
exp/_config.py            path resolution (no hardcoded machine paths; accepts
                          both data/results/figures and _data/_results/_final_figs)
exp/00_prepare.py         decode the Parquet release to PNG + manifest
exp/01_dup_audit.py       perceptual near-duplicate audit, calibrated on 429 known pairs
exp/02_embed_group.py     embedding-based grouping; tests whether filenames encode studies
exp/03_masks.py           intracranial + head masks (geometric, skull-ring fill)
exp/03b_cache.py          256 px memory-mapped caches (removes PNG decode from training)
exp/04_splits.py          random vs redundancy-aware split policies, 3 seeds
exp/05_train.py           one training run under the frozen protocol
exp/06_aggregate.py       aggregate runs, bootstrap CIs, leakage effect
exp/07_fig_audit.py       Figure 1
exp/08_gradcam_quant.py   attribution mass outside the intracranial compartment
exp/09_fig_results.py     Figure 2
exp/10_perclass.py        per-class ablation, model agreement, geometry control
exp/11_stats.py           paired bootstrap contrasts + mask-reliability sensitivity
exp/12_crossstream.py     cross-stream dependence of the trained model
exp/13_lesion_validate.py lesion containment + attribution scored against expert masks
exp/14_verify_numbers.py  machine check: manuscript numbers vs saved results
exp/15_protocol_audit.py  machine check: protocol identical across compared runs
build_manuscript.py       renders the manuscript .docx from the verified numbers
results/                  34 run records + all summary JSON files (shipped, so the
                          verification scripts run without retraining)
figures/                  the two figures used in the manuscript
```

## Data — not redistributed here

This repository contains **no images**. Obtain them yourself:

**Primary collection (classification).** TEKNO21 / TEKNOFEST-2021 stroke dataset, released by
the Turkish Ministry of Health open-data portal (`acikveri.saglik.gov.tr`) and described in
Koç et al., *Eurasian J. Med.* 54(3):248–258, 2022. We used the Hugging Face mirror
`BTX24/tekno21-brain-stroke-dataset-multi` (Parquet), which preserves the original release
filenames. That mirror carries an Apache-2.0 repository tag; **the tag applies to the
repository packaging, not to the underlying clinical collection**, whose conditions of use are
set by the issuing institutions. Confirm them at source before use.

**Expert lesion masks (validation only).** `Karrar-Alhdrawi/brain-stroke-ct-dataset`, a second
mirror of the same underlying collection, matched to ours by original filename. It is **not**
an independent dataset and is never used as external validation.

Place the Parquet shards in `data/` and run `exp/00_prepare.py`. The lesion masks, if you want
to reproduce the validation in Section IV-C, go in `lesionmasks/`.

## Environment

```bash
python -m venv .venv && . .venv/bin/activate      # Python 3.10
pip install -r requirements.txt
```

Trained on one NVIDIA RTX 4060 Ti (8 GB), PyTorch 2.5.1+cu121. CPU works but is slow.

Set `STROKE_AUDIT_ROOT` if the data live outside the checkout; otherwise paths resolve
relative to this directory.

## Reproducing the paper

```bash
python exp/00_prepare.py          # decode images + manifest
python exp/01_dup_audit.py        # redundancy audit
python exp/02_embed_group.py      # grouping + filename-structure test
python exp/03_masks.py            # intracranial and head masks
python exp/03b_cache.py           # 256 px caches
python exp/04_splits.py           # both split policies, seeds 0-2
bash  exp/run_all.sh              # the full training grid (34 runs)
python exp/06_aggregate.py        # aggregation + bootstrap CIs
python exp/10_perclass.py
python exp/11_stats.py            # paired bootstrap contrasts
python exp/12_crossstream.py      # cross-stream dependence
python exp/08_gradcam_quant.py
python exp/13_lesion_validate.py  # requires the mask mirror in lesionmasks/
python exp/07_fig_audit.py        # Figure 1
python exp/09_fig_results.py      # Figure 2
python exp/15_protocol_audit.py   # protocol uniformity check
python exp/14_verify_numbers.py   # manuscript-vs-results check
```

## Protocol

Identical for every run entering a comparison, and verified mechanically by
`exp/15_protocol_audit.py`: 70/15/15 stratified split, three seeds with the split regenerated
per seed, class-weighted cross-entropy, AdamW at 3e-4, cosine schedule, mixed precision,
batch size 48, 15 epochs, learning rate 3e-4, model selected on validation macro-F1 only, and
the test partition scored exactly once with the selected epoch. All 34 runs share these
settings; `exp/15_protocol_audit.py` asserts it and fails loudly if they ever diverge.

cuDNN autotuning and mixed precision mean runs reproduce to within the seed spread, not
bitwise.

## Two checks worth running on your own work

`15_protocol_audit.py` reads the saved run records and asserts that every configuration in a
headline comparison shares a protocol. It caught a real defect in our own experiments — one
group of runs had been trained at a different batch size — which we fixed by re-running rather
than by rewording the Methods.

`14_verify_numbers.py` re-reads the rendered manuscript and checks each headline number against
the result files, so a stale figure cannot survive a revision.

## Licence

Code: MIT (see `LICENSE`). The datasets are **not** covered by it; see *Data* above.
