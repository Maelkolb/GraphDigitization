# Run report: 20260702-221419-210051_tif_M11

- profile: **danube**
- graphdig: 0.1.0
- input: `pages/210051_M11.png` (669x185)

## Panels

| panel | label | bbox (x,y,w,h) | conf | flags |
|---|---|---|---|---|
| p01 | M11 | 0,0,669,185 | 1.00 | seeded_from_annotations |

![panels](overlays/panels.png)

## Calibration

| panel | unit | scale | slope (unit/px) | r2 | ticks used | flags |
|---|---|---|---|---|---|---|
| p01 | bavarian_foot | linear | -0.010782 | 1.0000 | 2/2 | seeded_from_annotations |

## Extraction (lineformer_local)

| panel | candidates | selected | conf | coverage | s_alpha | method |
|---|---|---|---|---|---|---|
| p01 | 100 | 36 | 0.008 | 1.000 | 0.692 | qc_reselect_gemini_pick |

## Series

### p01
- csv: `series/p01.csv` (30 samples, 0 gaps, baseline off)
- confidence chain: panel=1.00, calibration=1.00, extraction=0.01, coverage=1.00
- QC: **minor** The red curve follows the hand-drawn line well, with only slight vertical offsets in the trough around the sixth grid column.

![curve](overlays/curve_p01.png)
![series](overlays/reconstruction_p01.png)

## Review flags

| severity | stage | panel | reason |
|---|---|---|---|
| info | qc | p01 | QC rejected candidate; reselected cand 36 |
| warning | qc | p01 | minor deviation: The red curve follows the hand-drawn line well, with only slight vertical offsets in the trough around the sixth grid column. |
