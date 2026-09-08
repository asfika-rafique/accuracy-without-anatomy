# Data

No images are stored in this repository.

1. TEKNO21 / TEKNOFEST-2021 stroke collection — see the root README for provenance and
   licensing. Download the Parquet shards of the Hugging Face mirror
   `BTX24/tekno21-brain-stroke-dataset-multi` into `../_data/`, then run
   `python exp/00_prepare.py`.

2. Expert lesion masks, used only for the containment/attribution validation:
   `Karrar-Alhdrawi/brain-stroke-ct-dataset`, downloaded into `../_lesionmasks/`
   (`allow_patterns=["*/masks/*"]`). This is a mirror of the SAME underlying collection,
   not an independent dataset.

Conditions of use for the underlying clinical images are set by the issuing institutions
(Turkish Ministry of Health / TÜSEB), not by the mirrors. Confirm them at source.
