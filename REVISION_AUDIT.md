# Final JBHI manuscript and reproducibility audit

> Historical report for the REVISED manuscript. The locked FINAL PDF/DOCX,
> current README and VERIFICATION_FINAL.txt supersede version-specific details below.
> The locked manuscript has 21 references and a 210-word abstract.

Finalized 11 September 2026. This report supersedes the previous REVISION_AUDIT.md. It records finalization of the existing work, not new experiments. No training, attribution inference, or bootstrap experiment was rerun. Figures were regenerated from existing data/results to correct presentation.

## Outcome

The final manuscript is seven US Letter pages, with two figures, five tables and 18 cited references. The abstract is 245 whitespace-delimited tokens. The DOCX and Word-exported PDF agree. All seven PDF pages were inspected visually; affected pages were inspected again after the last corrections. No clipping, overlapping text, truncated confidence intervals, broken tables, or unreadable references were found. Fonts are embedded. The manuscript contains an active link to https://github.com/asfika-rafique/accuracy-without-anatomy.

The corrected local repository package is ready for a later GitHub update. **GitHub was not synchronized, as explicitly requested.** The public commit inspected was `1d7569ec1a7b7be3fb9238670c82340100e91311`. Publication/submission itself was not performed.

## Preserved scientific results

| Quantity | Verified final value | Existing evidence |
|---|---|---|
| TEKNO21 slices | 7,202; classes 1,290 / 1,361 / 4,551 | dup_stats.json; split/run records |
| Known duplicate pairs | 429 same-scan provenance pairs | dup_stats.json; Figure 1 inputs |
| DenseNet-201 grouped accuracy | 0.9661; 95% interval [0.9596, 0.9722] | summary.json; saved runs/predictions |
| ResNet-50 grouped accuracy | 0.9695; 95% interval [0.9633, 0.9753] | summary.json; saved runs/predictions |
| Random-versus-grouped inflation | +0.78 pp DenseNet-201; +1.33 pp ResNet-18 | summary.json; saved runs |
| Full-slice model on brain-only / brain-deleted input | 0.5660 / 0.6690 | crossstream.json |
| Exterior macro-AUC | 0.8342; accuracy is separately 0.6616 | summary.json; saved runs/predictions |
| Attribution enrichment | 2.68 times +/- 0.16 | attrib_multiseed.json |
| CAM mass outside brain | 66.6 +/- 0.6% | attrib_multiseed.json |
| Permutation accuracy | 0.4476 +/- 0.0240 | summary.json; three permutation run records |
| Permutation macro-AUC | 0.5107 +/- 0.0131 | summary.json; three permutation run records |

The 429 provenance pairs are not all pixel-identical: recorded dHash distances range from 0 to 5. The count and scientific analysis are unchanged. Cross-stream accuracies must not be confused with separately retrained brain-only/non-brain accuracies of 0.9056/0.9010. Historical seed-0 attribution fields remain in their original JSON files for provenance; attrib_multiseed.json supplies the final attribution. All original saved result JSON files are retained unchanged.

## Changes made

### Manuscript and builder

1. Restored the exact author presentation: **Tanha Asfika Jaman; Iftee Shekh Iftesham; Mst Lovely Akter; MOSTAFA FARZANA**, in that order. Spelled out corresponding author Tanha Asfika Jaman. Aligned the license's author capitalization without changing its terms.
2. Added the actual GitHub URL and hyperlink to Data, Code and Ethics Statements.
3. Removed the stray "Originally No" text and unsupported unconditional claim that no institutional approval was required. Retained the verifiable public/anonymised-data description and original collection's ethics citation [10]. Clarified that illustrative CT panels are included but the source dataset is not redistributed.
4. Limited lesion-exclusion claims to annotated pixels in the 2,214 scorable masks. Removed claims of complete tissue/anatomy absence and categorical identification of the shortcut's physical source. Preserved the imperfect-mask, out-of-distribution, causal-interpretation and patient-separation limitations.
5. Corrected the inference drawn from filename adjacency: 0.6236 versus 0.6235 does not establish patient independence. Grouping remains a calibrated lower bound on examination-level separation.
6. Matched preprocessing to code: 256-pixel cache, 224-pixel input, ImageNet normalization, and the actual crop/flip/rotation augmentation. Corrected provenance-table "from scratch" wording to ImageNet initialization.
7. Replaced obsolete single-seed attribution descriptions with three-checkpoint methods and actual usable sample counts: outside-brain 1,061/1,069/1,069; lesion attribution 335/329/333.
8. Matched statistical wording to implementation: Table II uses 5,000 pooled-prediction bootstrap draws; Table III combines 3,333 paired draws within each seed into 9,999 draws. Explicitly distinguished this mixture from a confidence interval for a seed-averaged or patient-level effect. Replaced zero-tail p < 0.0001 reporting with conservative p < 0.001; saved statistics and significance conclusions were preserved.
9. Corrected one non-headline Table II value: ResNet-18 random-split macro-AUC is the seed mean 0.9947 +/- 0.0043, rather than pooled 0.9946 paired with a seed SD.
10. Corrected cited-study results in [4] to 98.9% stroke detection, 98.5% ischaemia-versus-haemorrhage classification, and lesion IoU 0.952. Removed the unsupported 0.93 claim attributed to [2]; distinguished its collected/development-and-validation scans from a training-only count. Corrected E. Yagis's initial and narrowed other attribution/localization claims to what cited sources support.
11. Renumbered tables and callouts in physical order I-V. Kept table rows together and repeated headers, eliminating the orphaned first protocol-table row. Increased body text to 10 pt; retained the existing overall IEEE-style design and seven-page length.

### Figures

12. Extended Figure 2's architecture axis to display the complete ResNet-18 lower confidence limit; increased panel spacing and clarified stream labels.
13. Moved Figure 1's legend away from its plotted line. Updated anatomy/stream captions to reflect geometric masks and annotated-lesion validation.

### Reproducibility package

14. Added a portable 36-run launcher (`exp/run_all.py`) and replaced the machine-specific shell launcher with a wrapper. Made epochs/batch/learning rate explicit. Added preflight checks for records whose predictions or required checkpoints are missing; retained all three full-slice ResNet-18 checkpoints when training for later attribution. No training was launched.
15. Replaced the protocol checker with a failing-on-error audit of the exact 36-run, three-seed grid, protocol fields, validation-based selection, sample totals, split consistency and zero grouped leakage.
16. Replaced the stale manuscript-text-file numerical checker with direct DOCX/PDF support, explicit builder fallback, result aggregation and table-row checks, author/link checks and stale-text detection.
17. Required all three checkpoints for final multi-seed attribution instead of allowing an incomplete seed set to overwrite the final summary.
18. Updated README/data instructions for the actual dependency order, fresh rerun workspace, CUDA/Windows setup, saved-result verification, data layout, bootstrap interpretation and superseded seed-0 fields. Added ENVIRONMENT.md with the current original environment's direct dependency versions, explicitly not a historical lockfile.
19. Updated ignore rules for both directory layouts, excluding source datasets/checkpoints while retaining the final manuscript and reference predictions.
20. Packaged 36 saved prediction arrays and six split assignments alongside unchanged result JSON, final figures, manuscript, builder and scripts. Source CT datasets, lesion-mask datasets and model checkpoints are excluded. Replaced the stale audit with this report; supplied verification evidence and a SHA-256 manifest.

## Verification evidence and limits

- Protocol audit: all 36 records pass; 15 epochs, batch 48 and learning rate 0.0003 throughout the final grid.
- Numerical verifier: 263/263 checks passed for the finalized DOCX and separately for its PDF. DOCX verification includes table-row placement; PDF numerical presence checks complement, rather than replace, visual review.
- Independent recomputation of accuracy, macro-F1 and macro-AUC from all 36 saved prediction arrays matched the corresponding run records within 1e-12. This used saved outputs, not model inference.
- Negative tests demonstrated that the checkers reject a changed 12-epoch run record and a deliberately wrong manuscript table accuracy. These mutations were confined to a scratch fixture.
- All 18 references were checked against primary publication sources and all are cited. The particularly consequential correction was reference [4], not this paper's experiments.
- Final PDF: seven 612 x 792 pt pages; embedded fonts; two figures; five tables; active correct GitHub URI; no tracked changes/comments; no text blocks beyond page boundaries. Visual review covered figures, legends, axes, tables, captions, columns, page breaks and references.
- Full training from a clean environment was deliberately not rerun. Broad dependency bounds do not guarantee bitwise reproducibility. Saved checkpoints are not distributed, so regeneration of attribution requires retraining or separately obtaining the original checkpoints. No claim of fresh end-to-end reproduction is made.

## Current official JBHI requirements and budget

Checked the [official JBHI manuscript instructions](https://www.embs.org/jbhi/prepare-and-submit-your-manuscript/) during this audit. The regular-paper submission uses a single-spaced, two-column PDF with embedded figures/tables and an abstract of no more than 250 words. The final file satisfies these checked requirements; acceptance or portal approval is not guaranteed by a local audit.

For the **traditional/subscription route**, open access is optional. At seven pages the paper is below the eight-page mandatory-overlength threshold. The regular-paper page charge up to eight pages is voluntary; do not elect it or optional paid services for the stated $0 mandatory author-side budget. Preserve this limit if editors request revisions; mandatory overlength charges apply beyond eight pages. No OA purchase or paid service was introduced.

The official page also requires a cover letter, author ORCIDs, institutional email information and the multi-author consent form. It encourages suggested reviewers. These are submission-package/portal matters, not evidence of a scientific defect. The [official consent form](https://www.embs.org/jbhi/wp-content/uploads/sites/18/2026/08/jbhi-consent_form_v3-1_fixed.pdf) requires the authors' own signatures; none were fabricated or applied here. Originality, exclusive submission and all-author approval must be certified by the authors themselves.

Primary sources for corrected claims include [Yalcin and Vural](https://www.sciencedirect.com/science/article/pii/S001048252200676X), [Chilamkurthy et al.](https://pubmed.ncbi.nlm.nih.gov/30318264/), [Kuo et al.](https://pmc.ncbi.nlm.nih.gov/articles/PMC6842581/), [Yagis et al.](https://www.nature.com/articles/s41598-021-01681-w), and the [original TEKNOFEST collection paper](https://eajm.org/index.php/pub/article/view/3038).

## Final checklist

| Item | Status | Finding |
|---|---|---|
| Scientific consistency | PASS | Existing results preserved; inference limitations stated |
| Numerical consistency | PASS | 263 checks for each manuscript format; saved predictions independently verified |
| Authors | PASS | Exact four names/order; full corresponding-author name |
| Figures/tables | PASS | Two figures and five tables; display defects corrected |
| References | PASS | 18 cited references; substantive citation errors corrected |
| IEEE/JBHI format | PASS | Checked two-column PDF, embedded figures/tables, abstract and budget-related length requirements |
| GitHub link | PASS | Correct clickable URL in final PDF |
| GitHub reproducibility | WARNING | Corrected local package ready; public repository intentionally not synchronized; no fresh training rerun |
| Page count | PASS | Seven pages including references; one-page headroom below eight |
| Placeholders | PASS | None found in the final manuscript; no tracked changes/comments |
| Final PDF quality | PASS | All pages visually inspected; embedded fonts and clean layout |
| Submission readiness | WARNING | Manuscript file finalized; later GitHub synchronization and author/portal documents remain |

## Remaining actions

1. When authorized, synchronize the supplied repository package to GitHub so the public code matches this final version. No sync was performed.
2. Complete/confirm the cover letter, each author's ORCID and institutional details, signed author consent, and the submission declarations. Existing author email/affiliation text was preserved, not independently authenticated.
3. Submit the supplied PDF as a traditional regular paper, decline voluntary charges and optional paid services, and keep the final accepted version within eight pages to maintain the mandatory-fee budget.

No additional experiment or manuscript rewrite is identified as necessary by this audit.
