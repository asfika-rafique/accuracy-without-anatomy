# Accuracy Without Anatomy

Code and analysis for *"Accuracy Without Anatomy: A Redundancy and Shortcut Audit of a Public
Head-CT Stroke Benchmark."*

The paper audits the reliability of a public non-contrast head-CT stroke benchmark.
Substantial predictive signal remains outside the geometric intracranial compartment,
including beyond the segmented head. The non-brain stream retains some annotated lesion
content; exterior discrimination is not near-ceiling accuracy. These findings do not identify
causal features or establish clinical deployment readiness or external validity.

## Locked manuscript

The submission version is `JBHI_Stroke_CT_FINAL.pdf` (7 pages) and
`JBHI_Stroke_CT_FINAL.docx`, with 21 references, 5 tables and 2 figures.
These are exact copies of the locked files. `SHA256SUMS.txt` records package integrity.
`VERIFICATION_FINAL.txt` reports read-only checks; no experiments were run for this release.

---

## What this repository contains

The experimental results are produced by `exp/`. The manuscript builder contains explicit
text and table values, checked against saved results by `14_verify_numbers.py`; it is not a
dynamic analysis engine. Run the pipeline in the dependency order below.

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
exp/15_protocol_audit.py  fail-closed check of all 36 records and the three-seed grid
exp/16_attrib_multiseed.py final attribution over all three selected checkpoints
exp/run_all.py            portable final grid, with --dry-run for inspection
build_manuscript.py       renders the manuscript .docx from the verified numbers
results/                  36 run records + all summary JSON files (shipped, so the
                          verification scripts run without retraining)
figures/                  the two figures used in the manuscript
```

## Data — not redistributed here

This repository contains **no source CT dataset or lesion-mask files**; its paper figures
include illustrative CT panels. Obtain them yourself:

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
python exp/run_all.py             # the full training grid (36 runs); see fresh-workspace note
python exp/06_aggregate.py        # aggregation + bootstrap CIs
python exp/10_perclass.py
python exp/11_stats.py            # paired bootstrap contrasts
python exp/12_crossstream.py      # cross-stream dependence
python exp/08_gradcam_quant.py
python exp/13_lesion_validate.py  # containment and historical seed-0 attribution
python exp/16_attrib_multiseed.py # final three-seed attribution; requires three checkpoints
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
the test partition scored exactly once with the selected epoch. All 36 runs share these
settings; `exp/15_protocol_audit.py` asserts it and fails loudly if they ever diverge.

cuDNN autotuning and mixed precision mean runs reproduce to within the seed spread, not
bitwise.

## Two checks worth running on your own work

`15_protocol_audit.py` reads the saved run records and asserts that every configuration in a
headline comparison shares a protocol. It caught a real defect in our own experiments — one
group of runs had been trained for a different number of epochs — which we fixed by re-running rather
than by rewording the Methods.

`14_verify_numbers.py` checks run means/SDs, headline values, DOCX table rows, authors and the
repository URL. Use `--manuscript JBHI_Stroke_CT_FINAL.pdf` to check PDF text. Figure content
and layout still require visual review; the checker does not inspect raster plot labels.

## Licence

Code: MIT (see `LICENSE`). The datasets are **not** covered by it; see *Data* above.


## Finalization snapshot (11 September 2026)

Authors: **Tanha Asfika Jaman; Iftee Shekh Iftesham; Mst Lovely Akter; MOSTAFA FARZANA**.
Corresponding author: Tanha Asfika Jaman.

The 429 duplicate pairs are same-scan provenance pairs, not all pixel-identical files
(recorded dHash distances 0–5). Grouping is not verified patient separation.
The 0.5660 brain-only and 0.6690 brain-deleted accuracies are **cross-stream inference**
with full-slice models. Separately retrained brain/non-brain models reach 0.9056/0.9010.
Exterior **macro-AUC** is 0.8342; exterior accuracy is 0.6616.
Final permutation control: accuracy 0.4476 ± 0.0240, macro-AUC 0.5107 ± 0.0131.
Final attribution: enrichment 2.68 ± 0.16; outside-brain CAM mass 66.6 ± 0.6%.
`results/attrib_multiseed.json` supersedes the historical seed-0 attribution fields in
`gradcam_quant.json` and `lesion_validation.json`; the latter still supplies containment.

### Verify shipped results without training

`15_protocol_audit.py` uses the Python standard library only. The default numerical check
uses the shipped DOCX (standard-library XML extraction); if absent it checks builder
literals and says so. Explicit PDF checking needs PyMuPDF.

```bash
python exp/15_protocol_audit.py
python exp/14_verify_numbers.py
python exp/14_verify_numbers.py --manuscript JBHI_Stroke_CT_FINAL.pdf
python exp/run_all.py --dry-run
```

The package includes 36 run records and saved prediction arrays, summaries, split assignments,
the final figures and manuscript. It excludes model checkpoints and source clinical images.
The full training pipeline has not been rerun during finalization.

### Fresh workspace for a complete rerun

The trainer intentionally skips existing run JSON files. To retrain, set `STROKE_AUDIT_ROOT`
to a **fresh** directory before data preparation and use it for every step. Do not delete or
overwrite the shipped reference records. The launcher checks for missing predictions or
required checkpoints before accepting an existing run. It saves the three full-slice
ResNet-18 checkpoints needed by cross-stream inference and attribution.

POSIX: `export STROKE_AUDIT_ROOT=/path/to/fresh-audit`.
PowerShell: `$env:STROKE_AUDIT_ROOT='D:/fresh-audit'`.

Use Python 3.10. On Windows activate with `.venv/Scripts/Activate.ps1`; the Environment
example above uses a POSIX shell. Install the CUDA 12.1 PyTorch wheels with the command
in `requirements.txt` before installing the remaining requirements. `ENVIRONMENT.md`
records the originating machine's installed direct dependency versions. The broad bounds
in `requirements.txt` are compatibility ranges, not a bitwise reproduction lockfile.

Download the primary mirror's Parquet shards into the selected root's `data/` directory
(the `.parquet` files must be directly inside that directory). Download mask PNGs preserving
`lesionmasks/<class>/masks/<numeric-ID>.png`. See `data/README.md` for source URLs.

The statistical implementation uses 5000 pooled-prediction bootstrap draws for Table II,
and 3333 paired draws per seed, combined into 9999 draws, for Table III. The latter is a
mixture of within-seed distributions, not a confidence interval for a seed-averaged or
patient-level effect. Zero observed tail counts are reported conservatively as p < 0.001.
The unmodified saved JSON files retain their original empirical tail fractions.

### Rebuild manuscript

```bash
python build_manuscript.py
python exp/14_verify_numbers.py --manuscript JBHI_Stroke_CT_REBUILT.docx
```

The builder writes `JBHI_Stroke_CT_REBUILT.docx` without overwriting the locked files.
It needs python-docx and the two figure PNGs, but no training data. Export the rebuilt DOCX
to PDF using Word or a compatible office renderer, then inspect all pages and run the explicit
PDF check. Word was used for the final seven-page PDF. Office renderer versions can change
pagination. For a traditional JBHI submission with no mandatory overlength charge, keep the
final regular paper at eight pages or fewer including references; decline voluntary charges
and optional paid services. Open access is not required.

### Permutation and attribution controls

The final grid includes all three permuted-label full-slice ResNet-18 runs (seeds 0, 1, 2),
with 15 epochs, batch size 48 and learning rate 3e-4, like the other comparisons.
Their saved records and predictions are `results/runs/resnet18_grouped_full_s*_perm.*`.
Permutation macro-AUC is near chance; its accuracy must not be described as preserved
high classification performance.

The final Grad-CAM analysis uses the predicted class and the last convolutional block of
three selected full-slice ResNet-18 checkpoints. Scorable outside-intracranial counts are
1061/1069/1069; lesion-attribution counts are 335/329/333. Reported uncertainty is mean
and sample SD across seeds. The expert masks come from the same collection, not an
external validation cohort. Attribution is corroborative spatial evidence, not causality.

`REVISION_AUDIT.md` is a historical audit of the earlier revision, not the submission
instructions or current manuscript. The locked files and this README supersede its
version-specific descriptions. The final figure-panel title is "three tested backbones".
