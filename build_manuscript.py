# -*- coding: utf-8 -*-
"""Build the IEEE JBHI-format manuscript (two-column) as .docx."""
import os, json
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

import sys as _sys, os as _os
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "exp"))
from _config import ROOT, FIGS
OUT = _os.path.join(ROOT, "JBHI_Stroke_CT_REVISED.docx")

doc = Document()
s = doc.sections[0]
s.page_width, s.page_height = Inches(8.5), Inches(11)
s.top_margin, s.bottom_margin = Inches(0.72), Inches(0.9)
s.left_margin = s.right_margin = Inches(0.625)


def set_cols(section, n, space=340):
    sectPr = section._sectPr
    cols = sectPr.find(qn('w:cols'))
    if cols is None:
        cols = OxmlElement('w:cols'); sectPr.append(cols)
    cols.set(qn('w:num'), str(n)); cols.set(qn('w:space'), str(space))
    cols.set(qn('w:equalWidth'), '1')


set_cols(s, 1)
st = doc.styles['Normal']
st.font.name = 'Times New Roman'; st.font.size = Pt(9.5)
st.element.rPr.rFonts.set(qn('w:eastAsia'), 'Times New Roman')
st.paragraph_format.space_before = Pt(0); st.paragraph_format.space_after = Pt(0)
st.paragraph_format.line_spacing = 1.0


def P(text='', size=9.5, bold=False, italic=False, align='just', indent=0.0,
      before=0, after=0, allcaps=False):
    p = doc.add_paragraph()
    p.paragraph_format.first_line_indent = Inches(indent)
    p.paragraph_format.space_before = Pt(before); p.paragraph_format.space_after = Pt(after)
    p.alignment = {'just': WD_ALIGN_PARAGRAPH.JUSTIFY, 'c': WD_ALIGN_PARAGRAPH.CENTER,
                   'l': WD_ALIGN_PARAGRAPH.LEFT}[align]
    if text:
        r = p.add_run(text); r.font.size = Pt(size); r.bold = bold; r.italic = italic
        r.font.name = 'Times New Roman'
        if allcaps: r.font.all_caps = True
    return p


def RUNS(parts, size=9, align='just', indent=0.0, after=0):
    p = doc.add_paragraph()
    p.paragraph_format.first_line_indent = Inches(indent)
    p.paragraph_format.space_after = Pt(after)
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY if align == 'just' else WD_ALIGN_PARAGRAPH.CENTER
    for t, b, i in parts:
        r = p.add_run(t); r.font.size = Pt(size); r.bold = b; r.italic = i
        r.font.name = 'Times New Roman'
    return p


def H1(t): P(t, size=9.5, align='c', before=8, after=3, allcaps=True)
def H2(t): P(t, size=9.5, italic=True, align='l', before=4, after=1)
def BODY(t, first=False): P(t, size=9.5, align='just', indent=0.0 if first else 0.18)


def _newsec(n):
    sec = doc.add_section(WD_SECTION.CONTINUOUS)
    sec.page_width, sec.page_height = Inches(8.5), Inches(11)
    sec.top_margin, sec.bottom_margin = Inches(0.72), Inches(0.9)
    sec.left_margin = sec.right_margin = Inches(0.625)
    set_cols(sec, n)
    return sec


_FIGW = {"fig_audit.png": 7.16, "fig_results.png": 7.16, "fig_legacy.png": 6.4}


def FIGWIDE(fname, caption):
    _newsec(1)
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(3); p.paragraph_format.space_after = Pt(1)
    p.add_run().add_picture(os.path.join(FIGS, fname), width=Inches(_FIGW.get(fname, 7.16)))
    c = doc.add_paragraph(); c.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    c.paragraph_format.space_after = Pt(4)
    r = c.add_run(caption); r.font.size = Pt(7.5); r.font.name = 'Times New Roman'
    _newsec(2)


def _shade(cell, hexc):
    tcPr = cell._tc.get_or_add_tcPr()
    sh = OxmlElement('w:shd'); sh.set(qn('w:val'), 'clear')
    sh.set(qn('w:color'), 'auto'); sh.set(qn('w:fill'), hexc); tcPr.append(sh)


def TABLE(num, title, rows, widths, wide=False, notes=None, fs=7.5):
    if wide: _newsec(1)
    cap = doc.add_paragraph(); cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap.paragraph_format.space_before = Pt(5); cap.paragraph_format.space_after = Pt(1)
    r1 = cap.add_run('TABLE ' + str(num)); r1.font.size = Pt(7.5); r1.font.name = 'Times New Roman'
    cap.add_run().add_break()
    r2 = cap.add_run(title); r2.font.size = Pt(7.5); r2.font.name = 'Times New Roman'
    r2.font.all_caps = True
    t = doc.add_table(rows=0, cols=len(widths)); t.style = 'Table Grid'
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for ri, row in enumerate(rows):
        cells = t.add_row().cells
        for ci, txt in enumerate(row):
            cells[ci].width = Inches(widths[ci])
            para = cells[ci].paragraphs[0]
            para.paragraph_format.space_before = Pt(0.5); para.paragraph_format.space_after = Pt(0.5)
            para.alignment = WD_ALIGN_PARAGRAPH.CENTER if (ci > 0 or ri == 0) else WD_ALIGN_PARAGRAPH.LEFT
            run = para.add_run(txt); run.font.size = Pt(fs); run.font.name = 'Times New Roman'
            if ri == 0: run.bold = True; _shade(cells[ci], 'EFEFEF')
    if notes:
        n = doc.add_paragraph(); n.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        n.paragraph_format.space_after = Pt(4)
        rr = n.add_run(notes); rr.font.size = Pt(7); rr.font.name = 'Times New Roman'
    else:
        doc.add_paragraph().paragraph_format.space_after = Pt(3)
    if wide: _newsec(2)


# ============================ TITLE ==========================================
P('Accuracy Without Anatomy: A Redundancy and Shortcut Audit of a Public '
  'Head-CT Stroke Benchmark', size=17.5, align='c', after=7)
P('Tanha Asfika Jaman, Iftee Shekh Iftesham, Mst Lovely Akter, and Mostafa Farzana',
  size=10.5, align='c', after=2)
P('School of Computer Science, Nanjing University of Information Science and Technology, '
  'Nanjing 210044, China', size=8.5, align='c', after=1)
P('E-mail: 202353460049@nuist.edu.cn; 202353460052@nuist.edu.cn; 202353080157@nuist.edu.cn; '
  '202353080121@nuist.edu.cn', size=8.5, align='c', after=1)
P('Corresponding author: T. A. Jaman.', size=8.5, italic=True, align='c', after=7)

s2 = doc.add_section(WD_SECTION.CONTINUOUS)
s2.page_width, s2.page_height = Inches(8.5), Inches(11)
s2.top_margin, s2.bottom_margin = Inches(0.72), Inches(0.9)
s2.left_margin = s2.right_margin = Inches(0.625)
set_cols(s2, 2)

# ============================ ABSTRACT =======================================
RUNS([('Abstract\u2014', True, True),
      ('Objective: Three-way stroke labelling of non-contrast head computed tomography is '
       'widely reported at near-ceiling accuracy on small public collections. We ask what that '
       'accuracy actually measures. Methods: On the public TEKNOFEST-2021 release (7202 slices; '
       '1290 haemorrhagic, 1361 ischaemic, 4551 normal) we audited redundancy, calibrating a '
       'near-duplicate detector on 429 scans the release stores twice under different filenames. '
       'We then trained three networks under one frozen protocol with a held-out test partition, '
       'three seeds and bootstrap intervals, comparing a random against a redundancy-aware split, '
       'and retrained on four content streams: the full slice, the intracranial compartment '
       'alone, the head with that compartment deleted, and the region outside the head. '
       'Results: DenseNet-201 reached 0.966 accuracy (95 per cent interval 0.960 to 0.972), with '
       'ResNet-50 and ResNet-18 within one point. Test images with a training near-duplicate '
       'were classified at 0.998 versus 0.969 for the rest. Deleting the brain compartment reduced '
       'accuracy '
       'only from 0.961 to 0.901; the region outside the head alone still gave macro area under '
       'the curve 0.834 against 0.500 for chance; expert masks confirm that this stream contains '
       'no lesion tissue. A model trained on complete slices scored '
       'higher when the brain was deleted (0.669) than when everything except the brain was '
       'deleted (0.566). Permuting labels collapsed performance to '
       'chance, and removing the duplicated subset left every effect unchanged. Conclusion: Most '
       'of the reported accuracy is obtainable from image content outside the brain. Significance: Headline '
       'accuracy on this benchmark should not be interpreted as lesion recognition.',
       False, False)], size=8.5, after=4)

RUNS([('Index Terms\u2014', True, True),
      ('Benchmark evaluation, brain stroke, computed tomography, data leakage, medical image '
       'analysis, shortcut learning.', False, False)], size=8.5, after=5)

# ============================ I. INTRODUCTION ================================
H1('I. Introduction')
BODY('Stroke was the third leading cause of death worldwide in 2021 and a dominant cause of '
     'acquired adult disability [1]. Non-contrast computed tomography (NCCT) is the first-line '
     'examination because it is fast, ubiquitous and sufficient to exclude haemorrhage before '
     'thrombolysis, but hyperacute ischaemic change on NCCT is a low-contrast, spatially diffuse '
     'finding.', first=True)

BODY('Deep learning has produced convincing head-CT results where the target is dense, the '
     'cohort large and the reference standard strong: detectors for intracranial haemorrhage '
     'trained on hundreds of thousands of scans reach mean area under the receiver operating '
     'characteristic curve (AUC) of 0.93 across critical findings [2], and a single-centre model '
     'reached 0.991 against neuroradiologist consensus while also localizing the bleed [3]. A '
     'much larger and cheaper literature instead reports three-way stroke labelling '
     '(haemorrhagic / ischaemic / normal) on small public NCCT collections, commonly close to '
     'ceiling \u2014 for instance 99.35 per cent accuracy with lesion-segmentation '
     'intersection-over-union of 0.979 on Turkish Ministry of Health head-CT data [4].')

BODY('Numbers of that magnitude invite a question that is rarely asked of them: what is being '
     'measured? Two failure modes are well documented elsewhere in medical imaging. Models learn '
     'shortcuts \u2014 laterality tokens, support devices, acquisition signatures \u2014 rather '
     'than pathology [5]\u2013[7]; and leakage between partitions inflates reported performance '
     'across many fields [8], [9]. Neither has been measured on the stroke-CT collections that '
     'this literature relies on.')

BODY('This paper supplies that measurement. We do not propose an architecture. We take a widely '
     'used public NCCT stroke benchmark [10], audit it for redundancy, rebuild the evaluation '
     'under a frozen protocol with a held-out test partition, and then ask directly which parts '
     'of the image carry the label, by deleting anatomy and retraining. The contributions are: '
     '(i) a calibrated redundancy audit of the release, using 429 scans it stores twice as '
     'ground truth; (ii) a measurement of the leakage this redundancy causes, which is large on '
     'the affected subset and 0.8 to 1.3 points in aggregate; (iii) a content ablation showing '
     'that most of '
     'the reported accuracy survives deletion of the intracranial compartment, and that the label remains '
     'predictable far above chance from the scanner table and background alone; and (iv) '
     'a quantitative attribution analysis, scored against expert lesion masks, that agrees with (iii). All '
     'claims are supported by runs with three seeds, bootstrap intervals, a label-permutation '
     'control and a duplicate-exclusion control.')

# ============================ II. RELATED WORK ===============================
H1('II. Related Work')
BODY('Haemorrhage detection on head CT is the mature end of this field: Chilamkurthy et al. '
     'trained on 313318 scans from roughly twenty centres [2] and Kuo et al. reported '
     'expert-level performance with simultaneous localization [3]. Both validated where the '
     'model looks, not only the study label.', first=True)

BODY('Shortcut learning is the systematic explanation for high scores that do not transfer. '
     'Geirhos et al. framed it generally [5]; Zech et al. showed pneumonia classifiers keying on '
     'hospital-specific acquisition signatures [6]; DeGrave et al. showed COVID-19 radiograph '
     'models relying on content outside the lungs [7]. The standard probe is exactly the one we '
     'use: delete the region that must contain the pathology and see whether performance '
     'survives. To our knowledge this has not been applied to a stroke-CT benchmark.')

BODY('Leakage is the second systematic explanation. Kapoor and Narayanan documented it in 294 '
     'papers across 17 fields [8]; in imaging specifically, splitting multi-slice or '
     'multi-instance data at the image level inflates accuracy by 5 to 30 points, and by up to '
     '29 to 55 points in brain magnetic resonance imaging, where randomly labelled data reached '
     '96 per cent apparent accuracy under slice-level splitting [9], [11].')

BODY('Attribution maps are the usual interpretability evidence in this literature [12], but '
     'across eight saliency methods on two public radiology benchmarks every method failed at '
     'least one trustworthiness criterion and all were inferior to dedicated localizers [13]. We '
     'therefore treat attribution as a quantity to be measured, not as evidence.')

BODY('The TEKNOFEST-2021 (TEKNO21) collection [10] provides anonymised NCCT slices in three '
     'classes, curated from the Turkish Ministry of Health teleradiology archive and annotated '
     'by seven radiologists. It has become a common substrate for stroke classification work, '
     'and is the object of this audit.')

# ============================ III. METHODS ===================================
H1('III. Materials and Methods')

H2('A. Benchmark')
BODY('We used the public three-class TEKNO21 release [10] as distributed in Parquet form on the '
     'Hugging Face mirror named in the data statement, which preserves the original release filenames. It contains 7202 axial NCCT '
     'slices: 1290 haemorrhagic, 1361 ischaemic and 4551 normal, so the majority-class accuracy '
     'is 0.632. Images arrive as rendered 8-bit PNG, not DICOM; Hounsfield-unit windowing is '
     'therefore neither possible nor applied, although it is frequently described in papers '
     'using this release. Preprocessing was limited to resizing and scaling to the unit '
     'interval. The release carries no subject identifiers.', first=True)

H2('B. Redundancy Audit')
BODY('429 images are named "{class}_dcm_{ID}.png" and every one of those IDs also occurs as '
     '"{ID}.png" with an identical class label: the same scan is present twice under two '
     'filenames, rendered through two paths. These 429 pairs are ground truth for calibrating a '
     'near-duplicate detector.', first=True)

BODY('We computed a 256-bit difference hash per image. The 429 known pairs have median Hamming '
     'distance 0 (maximum 5); random pairs have median 102, with a first percentile of 66 '
     '[Fig. 1(a), (b)]. The two distributions are completely separated, so any threshold in a '
     'wide range is defensible; we used 6, the smallest value recovering 100 per cent of the '
     'known pairs [Fig. 1(c)]. Connected components of the resulting graph define redundancy '
     'groups.')

BODY('We also tested whether the original file numbering encodes examination structure, which '
     'would imply same-patient slices. It does not: mean cosine similarity between '
     'ImageNet-embedded images with adjacent identifiers is 0.6236, against a random-pair '
     'baseline of 0.6235. The release is decorrelated at the study level, so our groups capture '
     'genuine near-duplicates rather than patient clusters. Because subject identifiers are '
     'absent, these groups remain a lower bound on true examination-level grouping.')

FIGWIDE('fig_audit.png',
 'Fig. 1.  Redundancy audit and content streams. (a) The 429 scans that the release stores twice '
 'under two filenames give ground-truth same-scan pairs; their Hamming distances (median 0) are '
 'completely separated from random pairs (median 102), so the near-duplicate detector is '
 'calibrated rather than assumed. (b) One such pair. (c) Redundancy and known-pair recall against '
 'threshold; we use 6, the smallest value recovering all known pairs, at which 15.5 per cent of '
 'the collection lies in a redundancy group. (d)\u2013(g) The four content streams: full slice; '
 'intracranial compartment only; the head with all brain tissue deleted; and the region outside '
 'the head, which contains only background and the scanner head support.')



H2('C. Split Policies and Protocol')
BODY('Two policies were compared, identical in every other respect — architecture, epochs, '
     'batch size, learning rate, schedule and seeds, verified from the saved run records. The '
     'random policy performs an '
     'image-level stratified 70/15/15 split, which is what image-level evaluation on this '
     'collection amounts to. The grouped policy assigns whole redundancy groups, keeping every '
     'near-duplicate inside one partition. Under the random policy 15.6 to 16.1 per cent of test '
     'images have a training near-duplicate; under the grouped policy this is exactly zero, with '
     'class balance preserved to within one image per class.', first=True)

BODY('The full protocol is given in Table I and was fixed before any result was inspected: '
     'class-weighted cross-entropy, '
     'AdamW [16], cosine schedule, mixed precision [17], model selection on validation '
     'macro-F1 only, and '
     'the test partition scored once with the selected epoch. Every configuration was run with '
     'three seeds; the split is regenerated per seed, so the reported spread includes split '
     'variability. Interval estimates use two bootstraps over pooled test '
     'predictions: 5000 resamples for the single-configuration intervals of Table II, and '
     '10000 resamples paired over identical test images for the contrasts of Table V, where '
     'pairing removes between-image variance from the difference. '
     'Training used an NVIDIA RTX 4060 Ti (8 GB) with PyTorch 2.5.1; cuDNN autotuning and mixed '
     'precision make runs reproducible only to within the seed spread, not bitwise.')

TABLE('I', 'Benchmark Composition and Frozen Evaluation Protocol',
[["Item", "Value"],
 ["Collection", "TEKNO21 public three-class NCCT release [10]"],
 ["Images", "7202 axial slices, 8-bit PNG"],
 ["Classes (h / i / n)", "1290 / 1361 / 4551"],
 ["Majority-class accuracy", "0.632"],
 ["Provenance duplicates", "429 scans stored twice under two filenames"],
 ["Near-duplicate detector", "256-bit dHash, threshold 6"],
 ["   known-pair recall at threshold", "100 %  (median distance 0; random pairs 102)"],
 ["Images in a redundancy group", "1118  (15.5 %)"],
 ["Split", "70 / 15 / 15, stratified, three seeds"],
 ["   random policy: test leakage", "15.6\u201316.1 % of test has a train near-duplicate"],
 ["   grouped policy: test leakage", "0 %"],
 ["Model selection", "validation macro-F1 only"],
 ["Test partition", "scored once, with the selected epoch"],
 ["Optimiser / schedule", "AdamW [16], cosine, mixed precision [17]"],
 ["Loss", "class-weighted cross-entropy"],
 ["Epochs / batch size / learning rate", "15 / 48 / 3e-4, identical for every run"],
 ["Hardware / framework", "RTX 4060 Ti 8 GB, PyTorch 2.5.1+cu121"],
 ["Intervals", "5000-sample bootstrap (Table II); 10000-sample paired bootstrap (Table V)"]],
 [1.55, 1.75], wide=False, fs=7,
 notes='h = haemorrhagic, i = ischaemic, n = normal. The protocol was fixed before any result '
       'was inspected and is identical across every configuration reported.')



H2('D. Content Ablation')
BODY('To ask which image content carries the label we built four input streams from every slice '
     '[Fig. 1(d)\u2013(g)]. The full slice is unmodified. The intracranial compartment is '
     'defined geometrically as the region enclosed by the bright skull ring, deliberately not by '
     'intensity, so that hyperdense acute blood stays inside it; brain keeps that region only. '
     'Non-brain keeps the head with the intracranial compartment deleted, so it contains skull, '
     'scalp, orbits and skull base but no segmented brain. We do not assume this excludes the '
     'lesion; Section IV-C measures how far it does. Exterior deletes '
     'the entire head and keeps only background and the scanner head support, which cannot '
     'contain patient anatomy at all. Networks were retrained from ImageNet initialisation '
     'separately on each stream under the grouped policy. Three backbones were used: '
     'DenseNet-201 [14], ResNet-50 and ResNet-18 [15], spanning 11.2 to 23.5 million '
     'parameters, as capacity controls. Reporting follows the CLAIM '
     'checklist [18], and Table III records the provenance of every quantity.', first=True)

BODY('The claim that a stream excludes the lesion is geometric, so we validated it against expert '
     'annotation. A separately hosted mirror of the same collection distributes stroke '
     'segmentation masks; 6643 of its 6650 numeric filenames match ours, confirming a common '
     'source. Its mask semantics check out: all 1093 haemorrhagic and all 1130 ischaemic masks '
     'are non-empty, and all 4427 normal masks are empty. We resampled the 2223 lesion masks to '
     'our grid, of which 2214 survived a minimum-area threshold, and measured what fraction of '
     'annotated lesion pixels falls inside each of our masks (Section IV-C).')

BODY('Two controls accompany the ablation. Permuting all labels tests whether the pipeline can '
     'manufacture apparent performance. Repeating the ablation with the 429 duplicated images '
     'removed tests whether any effect is an artefact of that differently rendered subset.')

H2('E. Attribution')
BODY('Grad-CAM [12] was computed on the last convolutional block of the selected full-slice '
     'model over the 1061 test slices whose intracranial mask exceeds 100 pixels, and we '
     'measured the fraction of '
     'attribution mass falling outside the intracranial compartment against the fraction '
     'expected if attribution were uniform over the image.', first=True)

# ============================ IV. RESULTS ====================================
H1('IV. Results')

H2('A. Reproducible Near-Ceiling Classification')
BODY('Under the redundancy-aware protocol with a held-out test partition, DenseNet-201 reached '
     '0.9661 \u00b1 0.0053 accuracy (bootstrap interval 0.9596 to 0.9722), macro-F1 0.9551 and '
     'macro-AUC 0.9953 (Table II). ResNet-50 reached 0.9695 and ResNet-18 0.9605; the spread '
     'across three architectures whose parameter counts differ by a factor of 2.1 (11.2, 18.1 '
     'and 23.5 million) is 0.89 points, comparable to '
     'the within-architecture seed spread [Fig. 2(c)]. The near-ceiling result reported for this class of '
     'data is therefore reproducible and is not attributable to any particular architecture.',
     first=True)

FIGWIDE('fig_results.png',
 'Fig. 2.  (a) Content ablation under the redundancy-aware protocol (ResNet-18, three seeds, error '
 'bars are SD). Deleting the intracranial compartment costs only 5.9 accuracy points, and the region outside '
 'the head alone still gives macro-AUC 0.834 against 0.500 for chance. (b) Redundancy leakage on '
 'the random split: test images with a training near-duplicate are classified far more accurately '
 'than the rest, although this subset is small enough that the aggregate split effect is 0.8 to '
 '1.3 points. (c) Three architectures spanning 11.2 to 23.5 million parameters agree to within '
 '0.89 points, so architecture is not what limits performance on this benchmark.')

TABLE('II', 'Test-Set Results Under the Redundancy-Aware Protocol',
[["Configuration", "Input", "Accuracy", "Macro-F1", "Macro-AUC"],
 ["DenseNet-201", "full slice", "0.9661 \u00b1 0.0053", "0.9551 \u00b1 0.0081", "0.9953 \u00b1 0.0015"],
 ["ResNet-50", "full slice", "0.9695 \u00b1 0.0009", "0.9615 \u00b1 0.0019", "0.9937 \u00b1 0.0020"],
 ["ResNet-18", "full slice", "0.9605 \u00b1 0.0095", "0.9473 \u00b1 0.0130", "0.9919 \u00b1 0.0031"],
 ["ResNet-18", "brain only", "0.9056 \u00b1 0.0028", "0.8773 \u00b1 0.0068", "0.9693 \u00b1 0.0069"],
 ["ResNet-18", "non-brain (brain compartment deleted)", "0.9010 \u00b1 0.0088", "0.8773 \u00b1 0.0097", "0.9681 \u00b1 0.0065"],
 ["ResNet-18", "exterior (no head at all)", "0.6616 \u00b1 0.0273", "0.5985 \u00b1 0.0249", "0.8342 \u00b1 0.0148"],
 ["control: permuted labels", "full slice", "0.4476 \u00b1 0.0240", "0.3427 \u00b1 0.0131", "0.5107 \u00b1 0.0131"],
 ["control: duplicates removed", "full slice", "0.9616 \u00b1 0.0020", "0.9453 \u00b1 0.0053", "0.9940 \u00b1 0.0008"],
 ["control: duplicates removed", "non-brain", "0.9043 \u00b1 0.0134", "0.8720 \u00b1 0.0195", "0.9694 \u00b1 0.0071"],
 ["control: duplicates removed", "exterior", "0.6512 \u00b1 0.0267", "0.5816 \u00b1 0.0252", "0.8223 \u00b1 0.0191"],
 ["reference: majority class", "\u2013", "0.6319", "0.2582", "0.5000"],
 ["Random-split comparison", "", "", "", ""],
 ["DenseNet-201, random split", "full slice", "0.9739 \u00b1 0.0046", "0.9659 \u00b1 0.0052", "0.9966 \u00b1 0.0020"],
 ["   with train near-duplicate", "full slice", "0.9980", "\u2013", "\u2013"],
 ["   without near-duplicate", "full slice", "0.9693", "\u2013", "\u2013"],
 ["ResNet-18, random split", "full slice", "0.9739 \u00b1 0.0014", "0.9666 \u00b1 0.0019", "0.9946 \u00b1 0.0043"],
 ["   with train near-duplicate", "full slice", "0.9961", "\u2013", "\u2013"],
 ["   without near-duplicate", "full slice", "0.9697", "\u2013", "\u2013"]],
 [1.75, 1.55, 1.30, 1.25, 1.25], wide=True, fs=7,
 notes='Mean \u00b1 SD over three seeds (the split is regenerated per seed, so the spread includes '
       'split variability). Bootstrap 95 % intervals for the full-slice grouped runs: DenseNet-201 '
       'accuracy 0.9596\u20130.9722; ResNet-50 0.9633\u20130.9753; ResNet-18 0.9534\u20130.9670. The '
       'stratified rows partition the random-split test set by whether an image has a near-duplicate '
       'in training (n \u2248 171 and 912 respectively).')



H2('B. Redundancy Inflates Accuracy, Most Sharply on the Affected Subset')
BODY('Comparing split policies, the aggregate effect is present but modest: 0.9739 random against 0.9661 '
     'grouped for DenseNet-201 (+0.78 points) and 0.9739 against 0.9605 for ResNet-18 '
     '(+1.33 points). Both architectures are inflated by a redundancy-blind split, by between three quarters of a point and one and a third.', first=True)

BODY('Stratifying within the random split is more informative [Fig. 2(b)]. Test images that have '
     'a near-duplicate in training are classified at 0.9980 (DenseNet-201) and 0.9961 '
     '(ResNet-18), against 0.9693 and 0.9697 for the rest: gaps of 2.87 and 2.64 points on the '
     'affected subset. The aggregate effect is smaller only because that subset is about a sixth '
     'of the test set and the task is already near ceiling. The redundancy is real and its local '
     'effect is measurable; on a harder task, or a benchmark with more duplication, the same '
     'mechanism would move the headline number.')

H2('C. Most of the Accuracy Survives Deleting the Brain')
BODY('Deleting anatomy and retraining gives the central result [Fig. 2(a), Table II]. The full '
     'slice yields 0.9605 accuracy and macro-AUC 0.9919. Restricting the input to the '
     'intracranial compartment \u2014 the region that must anatomically contain the lesion \u2014 lowers '
     'accuracy to 0.9056. Deleting that compartment entirely and keeping only skull, scalp and '
     'skull base lowers it only to 0.9010 with macro-AUC 0.9681 — within half a point of the '
     'brain-only stream, and still 0.90 accuracy on a task whose majority class is 0.632.',
     first=True)

BODY('Validation against expert masks changes how much weight the non-brain stream can carry, and '
     'we report it plainly. Across 2214 annotated slices, a mean of 62.8 per cent of lesion '
     'pixels fall inside our geometric intracranial mask (median 92.2 per cent), but only '
     '51.0 per cent of slices reach 90 per cent containment, and the lowest decile is near '
     'zero \u2014 the skull-base slices where the bone ring is open. The non-brain stream is '
     'therefore not a clean lesion-free input: for a substantial minority of slices it retains '
     'part of the lesion, and its 0.9010 accuracy must be read with that caveat.')

BODY('The exterior stream is not affected by this, and it is the decisive one. Every annotated '
     'lesion pixel in all 2214 slices lies inside the head mask \u2014 containment is 1.000 '
     '— so a model restricted to the exterior sees no lesion tissue on any slice for which an expert annotation exists. With the entire head removed, leaving only '
     'background and the scanner head support, the three-way label is still recovered at '
     'macro-AUC 0.8342 \u00b1 0.0148 and accuracy 0.6616. Chance macro-AUC is 0.5. Content that '
     'verified to contain no lesion tissue therefore carries substantial label information. '
     'Since that content holds no anatomy, the information must originate in how the images were '
     'acquired, cropped or rendered rather than in pathology.')

BODY('Both controls behave as required. Permuting labels collapses the same pipeline, across three '
     'seeds, to 0.4476 \u00b1 0.0240 accuracy and macro-AUC 0.5107 \u00b1 0.0131, confirming that the protocol cannot manufacture performance. '
     'Removing the 429 duplicated images changes nothing: full 0.9616, non-brain 0.9043 '
     '(macro-AUC 0.9694), exterior 0.6512 (macro-AUC 0.8223). The shortcut is a property of the '
     'benchmark, not of its duplicated subset.')


BODY('These contrasts were tested with a paired bootstrap over identical test images, pooled '
     'across seeds (Table V). Restricting the input to the intracranial compartment costs 5.48 '
     'accuracy points (95 per cent interval 3.43 to 7.68, p < 0.0001). Deleting that compartment '
     'instead costs only 0.47 points relative to keeping it and nothing else (interval '
     '\u22122.04 to +2.96, p = 0.75). The interval excludes any advantage for the '
     'lesion-only stream larger than about three points, so this is a bounded null rather than a bare absence of significance. The exterior stream sits 23.9 '
     'points below the non-brain stream, but its macro-AUC interval of 0.801 to 0.862 excludes '
     'chance by a wide margin. Table V reports four contrasts; the three significant ones remain significant under Bonferroni correction for that family, and the fourth is a null that no correction can affect. The intervals are percentile bootstraps over pooled test predictions and so capture test-set sampling variability; between-seed variability is reported separately, as the standard deviations in Table II.')

BODY('Because the intracranial mask degrades where the skull ring is open, we repeated the '
     'comparison on the 986 test slices per seed whose intracranial mask exceeds 2 per cent '
     'of the image, a stricter criterion than the 100-pixel floor used for attribution. The ordering is unchanged: '
     'full 0.9605, brain-only 0.9233, non-brain 0.8954, exterior 0.6510. Excluding unreliable '
     'slices helps the brain-only stream, as expected, and opens a modest 2.8-point gap over the '
     'non-brain stream. Under either analysis the conclusion is the same: most of the '
     'achievable accuracy does not require brain tissue.')

TABLE('V', 'Paired Bootstrap Contrasts on Test Accuracy',
[["Contrast", "Difference", "95 % interval", "p"],
 ["full slice \u2212 brain only", "+0.0548", "+0.0343 to +0.0768", "< 0.0001"],
 ["brain only \u2212 non-brain", "+0.0047", "\u22120.0204 to +0.0296", "0.75"],
 ["full slice \u2212 non-brain", "+0.0597", "+0.0306 to +0.0851", "< 0.0001"],
 ["non-brain \u2212 exterior", "+0.2392", "+0.1739 to +0.2923", "< 0.0001"],
 ["exterior macro-AUC vs chance", "0.8342", "0.8007 to 0.8620", "chance = 0.500"]],
 [1.55, 0.85, 1.25, 0.85], wide=False, fs=7,
 notes='10000 resamples, paired over identical test images and pooled across three seeds '
       '(ResNet-18, redundancy-aware split). The second row is the key result: deleting the '
       'segmented intracranial compartment does not significantly change accuracy relative to '
       'keeping only that compartment.')

BODY('Two further analyses sharpen the interpretation. First, the per-class breakdown (Table IV) '
     'shows the effect is not confined to the subtle class. For haemorrhage, the class with the '
     'most conspicuous imaging finding, the non-brain stream reaches recall 0.866 and AUC 0.972, '
     'marginally above the brain-only stream (0.854, 0.972): deleting the blood does not degrade '
     'haemorrhage detection. Ischaemia behaves the same way (0.827 versus 0.825). Only the '
     'full-slice model, which sees both, does materially better.')

BODY('Second, the full-slice and non-brain models agree on 89.0 per cent of test images and are '
     'both correct on 87.8 per cent; only 8.2 per cent of images are cases the full-slice model '
     'gets right and the non-brain model does not. The two models are largely making the same '
     'decisions, which is difficult to reconcile with the full-slice model reasoning from lesion '
     'appearance.')

BODY('One obvious trivial explanation can be excluded. Image geometry does not encode the label: '
     '98.2, 97.1 and 95.9 per cent of haemorrhagic, ischaemic and normal images respectively are '
     '512 by 512, so a classifier cannot separate the classes from frame size. The signal is in '
     'the rendered content outside the brain, not in the file format.')

TABLE('IV', 'Per-Class Content Ablation (ResNet-18, Grouped Split, Three Seeds Pooled)',
[["Input stream", "Haemorrhagic", "Ischaemic", "Normal"],
 ["full slice", "0.942 / 0.995", "0.887 / 0.988", "0.988 / 0.992"],
 ["brain only", "0.854 / 0.972", "0.825 / 0.965", "0.944 / 0.971"],
 ["non-brain (brain compartment deleted)", "0.866 / 0.972", "0.827 / 0.966", "0.933 / 0.965"],
 ["exterior (no head at all)", "0.505 / 0.813", "0.697 / 0.838", "0.695 / 0.850"]],
 [1.60, 1.05, 1.05, 1.05], wide=False, fs=7,
 notes='Each cell is recall / one-versus-rest AUC. For haemorrhage \u2014 the class with the most '
       'conspicuous imaging finding \u2014 deleting the intracranial compartment does not reduce performance '
       'below the brain-only stream. Chance AUC is 0.500.')




H2('D. The Trained Model Depends on Extracranial Content')
BODY('The ablation above retrains on each stream, so it measures how much information a stream '
     'contains. A complementary question is whether the deployed full-slice model actually uses '
     'that information. We therefore took the three trained full-slice models and, without any '
     'retraining, evaluated them on the ablated inputs.', first=True)

BODY('The ordering is clear. On complete slices these models score 0.9599; given only the '
     'intracranial compartment they fall to 0.5660 (macro-AUC 0.7185), and given the head with '
     'the brain deleted they reach 0.6690 (macro-AUC 0.7793). The model is more accurate when '
     'the brain is removed than when everything except the brain is removed. With the patient '
     'deleted entirely it falls to 0.3356, below the majority-class rate, indicating that the '
     'collapse is not simply an artefact of masking per se. Both masked conditions are equally '
     'out-of-distribution for a model trained on complete slices, so the absolute values are not '
     'comparable with the retrained streams of Section IV-C; the ordering between them is the '
     'informative quantity, and it places extracranial content ahead of the brain.')

H2('E. Attribution Is Only Weakly Brain-Directed')
BODY('With expert masks available we can score attribution against the lesion itself rather '
     'than against the brain, and we repeat it on all three full-slice checkpoints rather than one. Grad-CAM places 3.83 \u00b1 0.22 per cent of '
     'its mass inside the annotated lesion, against a lesion area share of 1.43 per cent: an '
     'enrichment of 2.68 \u00b1 0.16 times over a uniform null. Attribution is therefore lesion-directed to '
     'a measurable but modest degree, and 96 per cent of its mass still falls outside the '
     'lesion.')

BODY('Measured against the brain instead, Grad-CAM placed 66.6 \u00b1 0.6 per cent of its mass outside the intracranial compartment, where '
     'uniform attribution would place 84.8 per cent: '
     'a measured-to-uniform ratio of 0.79. '
     'Attribution is thus only mildly biased toward the '
     'brain, and two thirds of it lies outside \u2014 consistent with a classifier that '
     'is substantially driven by extracranial content. Both quantities are stable across the three seeds.', first=True)

TABLE('III', 'Provenance of Every Reported Quantity',
[["Result", "Category", "Basis"],
 ["Benchmark composition, class counts, duplicate structure", "new measurement", "computed from the public release"],
 ["Near-duplicate calibration and grouping", "new measurement", "429 known same-scan pairs as ground truth"],
 ["Split-policy comparison and stratified leakage", "new controlled experiment", "3 seeds, frozen protocol, held-out test"],
 ["Architecture comparison", "new controlled experiment", "3 seeds each, bootstrap intervals"],
 ["Content ablation and both controls", "new controlled experiment", "3 seeds per stream, retrained from scratch"],
 ["Per-class ablation, model agreement, geometry check", "new measurement", "derived from saved test predictions"],
 ["Lesion containment and attribution-vs-lesion", "new measurement", "2214 expert masks from a mask-bearing mirror"],
 ["Cross-stream dependence of the trained model", "new controlled experiment", "3 checkpoints, inference only"],
 ["Grad-CAM mass outside the brain", "new measurement", "1061 test slices, selected model"]],
 [2.55, 1.45, 2.60], wide=True, fs=7,
 notes='Every quantity in this paper is newly produced. A \u201cnew measurement\u201d is computed '
       'directly from the released data or from stored test predictions; a \u201cnew controlled '
       'experiment\u201d involves training under the frozen protocol of Table I.')



# ============================ V. DISCUSSION ==================================
H1('V. Discussion')
BODY('The headline number of this benchmark does not mean what it appears to mean. Classification '
     'accuracy of 0.966 is real, reproducible under a rigorous protocol, robust to architecture, '
     'and survives every control we applied. It is also, to a large extent, not about the brain: '
     '0.901 of it is available with the intracranial compartment deleted, and a macro-AUC of '
     '0.834 is available with the patient removed from the image altogether — a stream that '
     'expert masks confirm contains no lesion pixel at all.', first=True)

BODY('The dependence test makes this concrete: a model trained on complete slices does better '
     'when the brain is deleted than when everything but the brain is deleted. Whatever it has '
     'learned, the intracranial compartment is not the principal carrier of it.')

BODY('The most economical explanation is an acquisition-level signature. The three diagnostic '
     'classes were assembled from different clinical populations and, plausibly, different '
     'scanners, protocols, reconstruction kernels, fields of view and patient positioning. Those '
     'differences are imprinted on the skull rendering, the field-of-view crop, the noise '
     'texture and the position of the head support, and a convolutional network will use them. '
     'This is the same mechanism Zech et al. found for hospital identity [6] and DeGrave et al. '
     'for content outside the lungs [7]; our contribution is to measure it, with controls, on a '
     'stroke-CT benchmark where it has not previously been quantified.')

BODY('The practical consequence is specific. A reported accuracy on this collection is not '
     'evidence of lesion recognition, and comparisons between architectures on it are '
     'uninformative: three networks from 11.2 to 23.5 million parameters agree to within 0.89 '
     'points, because they are all fitting the same non-anatomical signal. Papers that report '
     'only aggregate accuracy on such collections are therefore weakly constrained by their own '
     'evidence, and reviewers have a cheap remedy: require a content ablation. Retraining on a '
     'lesion-excluded stream costs one additional run and bounds how much of the score can be '
     'anatomical.')

BODY('Our redundancy finding is more nuanced than the leakage literature might predict. The '
     'duplication is unambiguous \u2014 429 scans stored twice, and 15.5 per cent of images in a '
     'near-duplicate group \u2014 and its effect on the affected subset is large, at about three '
     'points. The aggregate effect is smaller, 0.8 to 1.3 points, because that subset is about a sixth of the test set and the task saturates. Reporting '
     'only the aggregate difference between split policies would have hidden a real defect; the '
     'stratified comparison is the more sensitive instrument and we would encourage its use.')

BODY('Three practices would make results on collections of this kind interpretable, and none is '
     'expensive. Report a content ablation: retrain once on an input from which the lesion has '
     'been excluded, verifying that exclusion against annotation rather than assuming it, '
     'and quote that number beside the headline accuracy, since the gap bounds how much of the '
     'score can be anatomical. Report the geometry of any redundancy: a perceptual hash over the '
     'collection takes minutes, and stratifying the test set by whether an image has a training '
     'near-duplicate is more sensitive than comparing split policies in aggregate. Treat '
     'attribution as a measurement rather than an illustration — the fraction of mass falling '
     'inside the structure that is supposed to drive the decision is a single number, and it is '
     'more informative than any overlay.')

BODY('Clinically, none of this supports deployment, and we make no such claim. A model that '
     'separates classes using scanner signatures will fail the moment the scanner changes, which '
     'is precisely the situation of external validation. Subtype assignment on NCCT determines '
     'whether a patient receives thrombolysis or surgery, and no reader comparison, calibration '
     'analysis or prospective evaluation was performed here. The appropriate reading of this '
     'benchmark is as a computer-vision exercise whose headline metric is not anchored to the '
     'clinical task.')

# ============================ VI. LIMITATIONS ================================
H1('VI. Limitations')
BODY('The intracranial masks are algorithmic, not expert. They are defined geometrically to keep '
     'hyperdense blood inside the compartment, but at the skull base the ring is open and the '
     'mask degrades; 384 slices had essentially empty masks and were retained in training but '
     'excluded from the attribution analysis. Imperfect masks could leak a little lesion signal '
     'into the non-brain stream, and the expert-mask validation shows it does so for a '
     'substantial minority of slices; this is why we rest the argument on the exterior stream, '
     'whose lesion-free status is verified rather than assumed. The sensitivity analysis '
     'restricted to reliable masks '
     '(Section IV-C) addresses this and leaves the ordering unchanged. The exterior stream '
     '\u2014 verified against expert annotation to contain no '
     'lesion tissue \u2014 carries the argument.', first=True)

BODY('Subject-level separation cannot be verified, since the release omits identifiers. Our '
     'grouping is a calibrated lower bound on it, and the embedding analysis indicates the '
     'release is decorrelated at the study level, but a true patient-level split remains '
     'unavailable and would require the DICOM release.')

BODY('The content ablation identifies that non-anatomical information is present and sufficient; '
     'it does not identify which physical factor supplies it. Attributing the signal to specific '
     'acquisition parameters would need scanner and protocol metadata that the public release '
     'does not carry.')

BODY('Findings are confined to one collection from one national health system, and to 2D slice '
     'classification. Finally, runs are reproducible only to within the seed spread, not '
     'bitwise.')

# ============================ VII. CONCLUSION ================================
H1('VII. Conclusion')
BODY('We audited a widely used public head-CT stroke benchmark and found that its near-ceiling '
     'accuracy is reproducible, architecture-independent, and largely non-anatomical. With the '
     'intracranial compartment deleted a classifier still reaches 0.901 accuracy; with the '
     'patient removed from the image entirely — a stream that expert masks confirm holds no '
     'lesion pixel in any annotated slice — it still reaches macro-AUC 0.834. Redundancy in the release inflates '
     'performance by about three points on the affected sixth of the test set, and by 0.8 to 1.3 points overall. Reported accuracy '
     'on this benchmark should not be read as lesion recognition, and a content ablation \u2014 '
     'one extra training run \u2014 is enough to reveal it.', first=True)

# ============================ STATEMENTS =====================================
H1('Data, Code and Ethics Statements')
BODY('Data: the public TEKNO21 head-CT stroke collection [10], obtained from the Hugging Face '
     'mirror BTX24/tekno21-brain-stroke-dataset-multi, which carries an Apache-2.0 repository '
     'tag; the underlying collection was released by the Turkish Ministry of Health open-data '
     'portal and its conditions of use are set by the issuing institutions rather than by '
     'the mirror, so intending users should confirm them at source. The expert stroke masks '
     'used only for the containment and attribution validation of Section IV-C come from a '
     'second mirror of the same collection, Karrar-Alhdrawi/brain-stroke-ct-dataset, matched '
     'to ours by original filename. Originally '
     'No images are redistributed with this paper and no new patient data were '
     'collected. Ethics: analysis used only anonymised, publicly released images; ethical '
     'approval for the original collection and annotation is reported in [10], and no '
     'institutional review board approval was required for this secondary analysis. Code: all '
     'audit, training, ablation and analysis scripts, together with the two tools used to '
     'verify protocol uniformity across runs and to cross-check every number reported here '
     'against the stored result files, are available from the corresponding author. The '
     'authors declare no competing interests.', first=True)

# ============================ REFERENCES =====================================
H1('References')
refs = [


 'GBD 2021 Stroke Risk Factor Collaborators, "Global, regional, and national burden of stroke '
 'and its risk factors, 1990\u20132021: a systematic analysis for the Global Burden of Disease '
 'Study 2021," Lancet Neurol., vol. 23, no. 10, pp. 973\u20131003, 2024.',

 'S. Chilamkurthy et al., "Deep learning algorithms for detection of critical findings in head '
 'CT scans: a retrospective study," Lancet, vol. 392, no. 10162, pp. 2388\u20132396, 2018.',

 'W. Kuo, C. H\u00e4ne, P. Mukherjee, J. Malik, and E. L. Yuh, "Expert-level detection of acute '
 'intracranial hemorrhage on head computed tomography using deep learning," Proc. Natl. Acad. '
 'Sci. USA, vol. 116, no. 45, pp. 22737\u201322745, 2019.',

 'S. Yal\u00e7\u0131n and H. Vural, "Brain stroke classification and segmentation using '
 'encoder-decoder based deep convolutional neural networks," Comput. Biol. Med., vol. 149, '
 'art. 105941, 2022.',

 'R. Geirhos et al., "Shortcut learning in deep neural networks," Nature Mach. Intell., vol. 2, '
 'pp. 665\u2013673, 2020.',

 'J. R. Zech, M. A. Badgeley, M. Liu, A. B. Costa, J. J. Titano, and E. K. Oermann, "Variable '
 'generalization performance of a deep learning model to detect pneumonia in chest radiographs: '
 'A cross-sectional study," PLoS Med., vol. 15, no. 11, art. e1002683, 2018.',

 'A. J. DeGrave, J. D. Janizek, and S.-I. Lee, "AI for radiographic COVID-19 detection selects '
 'shortcuts over signal," Nature Mach. Intell., vol. 3, pp. 610\u2013619, 2021.',

 'S. Kapoor and A. Narayanan, "Leakage and the reproducibility crisis in machine-learning-based '
 'science," Patterns, vol. 4, no. 9, art. 100804, 2023.',

 'S. Yagis et al., "Effect of data leakage in brain MRI classification using 2D convolutional '
 'neural networks," Sci. Rep., vol. 11, art. 22544, 2021.',

 'U. Ko\u00e7 et al., "Artificial intelligence in healthcare competition (TEKNOFEST-2021): '
 'Stroke data set," Eurasian J. Med., vol. 54, no. 3, pp. 248\u2013258, 2022.',

 'I. E. Tampu, A. Eklund, and N. Haj-Hosseini, "Inflation of test accuracy due to data leakage '
 'in deep learning-based classification of OCT images," Sci. Data, vol. 9, art. 580, 2022.',

 'R. R. Selvaraju, M. Cogswell, A. Das, R. Vedantam, D. Parikh, and D. Batra, "Grad-CAM: Visual '
 'explanations from deep networks via gradient-based localization," in Proc. IEEE ICCV, 2017, '
 'pp. 618\u2013626.',

 'N. Arun et al., "Assessing the trustworthiness of saliency maps for localizing abnormalities '
 'in medical imaging," Radiol. Artif. Intell., vol. 3, no. 6, art. e200267, 2021.',

 'G. Huang, Z. Liu, L. van der Maaten, and K. Q. Weinberger, "Densely connected convolutional '
 'networks," in Proc. IEEE CVPR, 2017, pp. 4700\u20134708.',

 'K. He, X. Zhang, S. Ren, and J. Sun, "Deep residual learning for image recognition," in Proc. '
 'IEEE CVPR, 2016, pp. 770\u2013778.',

 'I. Loshchilov and F. Hutter, "Decoupled weight decay regularization," in Proc. ICLR, 2019.',

 'P. Micikevicius et al., "Mixed precision training," in Proc. ICLR, 2018.',

 'J. Mongan, L. Moy, and C. E. Kahn, "Checklist for artificial intelligence in medical imaging '
 '(CLAIM): A guide for authors and reviewers," Radiol. Artif. Intell., vol. 2, no. 2, '
 'art. e200029, 2020.',
]
for i, r in enumerate(refs, 1):
    p = doc.add_paragraph()
    p.paragraph_format.first_line_indent = Inches(-0.15)
    p.paragraph_format.left_indent = Inches(0.15)
    p.paragraph_format.space_after = Pt(0.5)
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    run = p.add_run('[%d] %s' % (i, r))
    run.font.size = Pt(7.5); run.font.name = 'Times New Roman'

# A trailing continuous section break makes Word balance the two columns of the
# reference list instead of leaving the right-hand column of the last page empty.
_bal = doc.add_section(WD_SECTION.CONTINUOUS)
_bal.page_width, _bal.page_height = Inches(8.5), Inches(11)
_bal.top_margin, _bal.bottom_margin = Inches(0.72), Inches(0.9)
_bal.left_margin = _bal.right_margin = Inches(0.625)
set_cols(_bal, 2)

doc.save(OUT)
print('saved', OUT)
