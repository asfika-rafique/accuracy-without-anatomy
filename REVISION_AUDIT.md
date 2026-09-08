# Final JBHI Audit — Accuracy Without Anatomy

**Manuscript:** `JBHI_Stroke_CT_REVISED.docx` / `.pdf` — **7 rendered pages** (limit 8), abstract
246 words (limit 250), 18 references all cited, 5 tables, 2 figures.

**Authors (final, order preserved):** Tanha Asfika Jaman · Iftee Shekh Iftesham ·
Mst Lovely Akter · Mostafa Farzana. Corresponding: T. A. Jaman.

**Machine checks (run them yourself):**
`python exp/15_protocol_audit.py` — protocol uniformity across all 34 runs
`python exp/14_verify_numbers.py` — manuscript numbers vs saved result files

---

## A. Problems found, severity, and how each was fixed

| # | Problem | Severity | Fixed? | How |
|---|---|---|---|---|
| 1 | **Author 4's name silently reordered** to "Farzana Mostafa" | High (authorship) | yes | Restored to **Mostafa Farzana** as given. Given/family-name assignment flagged for you to confirm. |
| 2 | **Epochs differed by architecture** (12 for DenseNet-201/ResNet-50, 15 for ResNet-18) while the paper claimed an identical protocol | High | yes | **Re-ran 9 runs at 15 epochs.** All 34 runs now share epochs/batch/lr, verified mechanically. |
| 3 | `exp/` scripts all hardcoded `D:/paper publish` | High (reproducibility) | yes | Added `exp/_config.py`; 17 scripts de-pathed; `STROKE_AUDIT_ROOT` override. Zero absolute paths remain. |
| 4 | Contribution (iv) still cited the deleted YOLOv8 section | High (dangling claim) | yes | Rewritten to the attribution analysis. |
| 5 | Abstract said architectures agree "within 0.2 points" | Medium | yes | Corrected to "within one point" (measured spread 0.89). |
| 6 | Leakage described as "an honest null" | Medium (now false) | yes | Under the uniform protocol **both** architectures inflate: **+0.78 pp** (DenseNet), **+1.33 pp** (ResNet-18). Text, abstract, discussion rewritten. |
| 7 | Table I batch listed as "24–64" | Medium | yes | Now "15 / 48 / 3×10⁻⁴, identical for every run". |
| 8 | Methods §III-E heading still "Attribution and **Legacy Localization**" | Medium | yes | Renamed to "Attribution". |
| 9 | Fig. 1 caption said "all brain tissue deleted" | Medium (overclaim) | yes | Now "that compartment deleted", plus a note that the non-brain stream is not assumed lesion-free. |
| 10 | Reference [18] (Q-YOLOv8) orphaned after the YOLO cut | Medium | yes | Removed; renumbered to 18 references, all cited. |
| 11 | References left the last page 3/4 empty | Low (layout) | yes | Trailing continuous section break balances the columns. |
| 12 | Split-policy claim "identical in everything else" was unverified | Medium | yes | Now names the fields, *verified from the saved run records*. |
| 13 | Stale values after re-runs (0.9701, 0.9682, 0.9705, 0.9943, 0.9949, 0.9653, 3.27, +0.04, 0.96 points, 0.970) | High | yes | 18 value-level updates; stale-number sweep now returns clean. |

### Carried over and re-verified as still correct
- "Lesion-free" appears **once**, on the **exterior** stream only (containment 1.000). The
  non-brain stream is never called lesion-free.
- No YOLO material anywhere; every quantity is newly produced.
- Data statement declares both mirrors and does not attribute the mirror's Apache-2.0 tag to the
  underlying clinical collection.
- Parameter counts stated as measured (11.2 / 18.1 / 23.5 M); no "order of magnitude".

---

## B. Experiments re-run this round

| Runs | Reason | Protocol | Result |
|---|---|---|---|
| `densenet201_grouped_full_s{0,1,2}` | epoch mismatch vs ResNet-18 | 15 ep, bs 48, lr 3e-4 | **0.9661 ± 0.0053** (was 0.9701 @ 12 ep) |
| `densenet201_random_full_s{0,1,2}` | keep split-policy pairing consistent | same | **0.9739 ± 0.0046** |
| `resnet50_grouped_full_s{0,1,2}` | epoch mismatch | same | **0.9695 ± 0.0009** |

Consequence: the leakage effect became **consistently positive** across architectures instead of
a null for DenseNet — a more coherent and more honest result than before.

---

## C. Final verified numbers (all traced to `_results/`)

**Classification — redundancy-aware split, held-out test, 3 seeds**
DenseNet-201 **0.9661** [0.9596, 0.9722] · ResNet-50 **0.9695** [0.9633, 0.9753] ·
ResNet-18 **0.9605** [0.9534, 0.9670] — spread **0.89 pp**

**Redundancy / leakage**
15.5 % of images in a redundancy group · random split leaves 15.6–16.1 % of test in
near-duplicate contact with train, grouped split 0 % · aggregate inflation **+0.78 pp**
(DenseNet), **+1.33 pp** (ResNet-18) · stratified: leaked **0.9980 / 0.9961** vs clean
**0.9693 / 0.9697**

**Content ablation (ResNet-18, identical protocol)**
full **0.9605** · brain-only **0.9056** · non-brain **0.9010** · exterior **0.6616**
(macro-AUC **0.8342** [0.8007, 0.8620]; chance 0.500; majority class 0.632)

**Paired bootstrap, 10 000 resamples**
full − brain **+0.0548** [+0.0343, +0.0768] p<0.0001 · brain − non-brain **+0.0047**
[−0.0204, +0.0296] **p = 0.75** · non-brain − exterior **+0.2392** p<0.0001

**Controls** permuted labels 0.4302 (AUC 0.5243) · duplicates removed: full 0.9616,
non-brain 0.9043, exterior 0.6512 (AUC 0.8223)

**Cross-stream dependence** full-slice models scored **0.6690 with the brain deleted** vs
**0.5660 with only the brain**

**Expert-mask validation** 2 214 scorable lesion masks · containment in intracranial mask
**62.8 %** (median 92.2 %) · containment in head mask **1.0000** · Grad-CAM enrichment in lesion
**2.76×**

---

## D. Remaining limitations (genuinely unresolvable here)

1. **Single benchmark.** Both available mirrors are the *same* TEKNOFEST source (6 643/6 650
   filenames match ours). RSNA ICH is a different task at ~100 GB and would not test this
   three-class claim. No independent same-task dataset was found.
2. **Physical cause of the shortcut unidentified.** Non-anatomical information is present and
   sufficient; which acquisition factor supplies it is unknown. Needs the DICOM release with
   scanner/protocol metadata. The paper does not claim the head support is causally responsible.
3. **Subject-level splitting impossible** — the release carries no identifiers. Our grouping is a
   calibrated lower bound; the embedding test shows the release is decorrelated at study level.
4. **Non-brain stream is not cleanly lesion-free** (62.8 % containment). Stated plainly; the
   argument rests on the exterior stream, whose lesion-free status is verified.
5. **Attribution is single-seed** (seed-0 checkpoint), stated as such.
6. **384 slices** have degenerate intracranial masks; the sensitivity analysis excludes them and
   the ordering is unchanged.
7. Runs reproduce to within the seed spread, not bitwise (cuDNN autotuning + mixed precision).

---

## E. Final JBHI review

| Criterion | Score |
|---|---|
| Novelty | 6.5 / 10 — established probe design, but the first such audit of this benchmark |
| Methodology | 8.5 / 10 — uniform protocol, held-out test, three controls, machine-verified |
| Reproducibility | 9 / 10 — full pipeline, no hardcoded paths, two self-audit scripts |
| Statistical rigour | 8.5 / 10 — paired bootstrap, CIs, seeds; no multiplicity correction |
| Clinical relevance | 6 / 10 — matters for practice, but no clinical validation and none claimed |
| Writing | 8.5 / 10 |
| JBHI fit | 7 / 10 — squarely health informatics; audit papers less common than method papers |

## F. Editorial recommendation: **Minor Revision**

Not Accept: the single-benchmark scope is a legitimate limitation an editor may want addressed,
and the shortcut's physical cause is unidentified. Not Major Revision: the protocol defect is
fixed by re-running, every claim matches evidence, controls are present, terminology matches the
validation, and remaining gaps are explicitly labelled. What is left needs *new data*, not
revision of this manuscript.

## G. Submission status — manuscript is clean

The manuscript contains **no placeholders of any kind** (verified: 0 occurrences of `[[TBD`,
`TODO`, `FIXME`, `placeholder`). ORCIDs were removed from the PDF because IEEE collects them in
the Author Portal, not in the manuscript body. The code-availability statement is complete and
truthful without an invented URL.

Author IDs confirmed by the corresponding author: Mst Lovely Akter `202353080157`,
Mostafa Farzana `202353080121`.

Remaining items are **submission-portal only** — nothing further is needed in the document:

1. Link the four ORCIDs in the IEEE Author Portal.
2. Signed Author Consent form (multi-author).
3. Four suggested reviewers from institutions other than NUIST.
4. Cover letter stating innovation and significance relative to JBHI scope.
5. At Article Setup: **decline voluntary page charges, decline open access, decline
   colour-in-print** — this is what keeps the mandatory cost at $0.
6. Optional: add the public repository URL to the code statement once the GitHub repo is live.


---

## FINAL PRE-SUBMISSION AUDIT (3 reviewers + handling editor)

Nine further issues were found in the finalized manuscript. All A and B issues are fixed; two
required new runs.

| # | Issue | Class | Fixed | How |
|---|---|---|---|---|
| F1 | Fig. 2(b) caption said the aggregate split effect "stays under one point" — false after the 15-epoch re-runs (+0.78 / +1.33) | A | yes | Caption now states 0.8 to 1.3 points |
| F2 | Section IV-B heading "Redundancy Produces **Local, Not Aggregate**, Inflation" contradicted its own body | A | yes | Retitled "Redundancy Inflates Accuracy, Most Sharply on the Affected Subset" |
| F3 | Permuted-label control had **one seed** while every other row had three | A | yes | **Ran seeds 1–2.** Now 0.4476 ± 0.0240 acc, 0.5107 ± 0.0131 AUC over 3 seeds |
| F4 | Attribution analysis was **seed-0 only** (a stated limitation) | A | yes | **New `exp/16_attrib_multiseed.py` over all 3 checkpoints.** Enrichment 2.68× ± 0.16; CAM outside brain 66.6 ± 0.6 %. Limitation removed |
| F5 | No multiple-comparison statement for the four contrasts in Table V | A | yes | States the three significant contrasts survive Bonferroni and the fourth is a null; also states what the bootstrap intervals do and do not capture |
| F6 | p = 0.75 reported as bare non-significance | B | yes | Reframed as a **bounded null**: the interval excludes any lesion-only advantage above ~3 points |
| F7 | "provably never sees lesion tissue" / "no patient tissue whatsoever" — stronger than what was verified | B | yes | Now "no lesion tissue on any slice for which an expert annotation exists"; three occurrences corrected incl. Limitations and Conclusion |
| F8 | "the only region that can contain the lesion" conflated our geometric mask with the anatomical compartment | B | yes | "the region that must anatomically contain the lesion" |
| F9 | "The result is unambiguous" / "confirming" / "well inside the seed spread" | B | yes | Softened to "The ordering is clear" / "indicating" / "comparable to the within-architecture seed spread" |

**Verification after fixes:** 38/40 headline numbers auto-verified (the 2 exceptions are values the
manuscript does not quote); protocol audit reports 0 mismatches across all 36 runs; 0 placeholders;
0 uncited references; 7 pages; abstract 246 words.

## H. Files

The GitHub package is assembled at `github_package/` (71 files, 1.3 MB): code, all 34 run
records, summary JSON, both figures, README, requirements, MIT licence, .gitignore and data
instructions. No images, checkpoints, secrets or restricted data. Verified to run standalone.


`JBHI_Stroke_CT_REVISED.docx` · `JBHI_Stroke_CT_REVISED.pdf` (7 pages) · `build_manuscript.py` ·
`exp/` (18 scripts incl. `_config.py`, `14_verify_numbers.py`, `15_protocol_audit.py`) ·
`_results/` (34 run records + summaries) · `README.md` · `requirements.txt` · `LICENSE` ·
`.gitignore` · `data/README.md`
