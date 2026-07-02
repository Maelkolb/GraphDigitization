# Run report: 20260702-221151-210051_tif_M02

- profile: **danube**
- graphdig: 0.1.0
- input: `pages/210051_M02.png` (619x854)

## Panels

| panel | label | bbox (x,y,w,h) | conf | flags |
|---|---|---|---|---|
| p01 | M02 | 0,0,619,854 | 1.00 | seeded_from_annotations |

![panels](overlays/panels.png)

## Calibration

| panel | unit | scale | slope (unit/px) | r2 | ticks used | flags |
|---|---|---|---|---|---|---|
| p01 | bavarian_foot | linear | -0.010782 | 1.0000 | 2/2 | seeded_from_annotations |

## Extraction (lineformer_local)

| panel | candidates | selected | conf | coverage | s_alpha | method |
|---|---|---|---|---|---|---|
| p01 | 99 | 57 | 0.002 | 1.000 | 0.691 | qc_reselect_gemini_pick |

## Series

### p01
- csv: `series/p01.csv` (28 samples, 0 gaps, baseline off)
- confidence chain: panel=1.00, calibration=1.00, extraction=0.00, coverage=1.00
- QC: **ok** The red curve tracks the original hand-drawn curve extremely well with no noticeable deviations.

![curve](overlays/curve_p01.png)
![series](overlays/reconstruction_p01.png)

## Review flags

| severity | stage | panel | reason |
|---|---|---|---|
| info | qc | p01 | QC rejected candidate; reselected cand 57 |
