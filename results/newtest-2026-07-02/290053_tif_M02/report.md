# Run report: 20260702-221445-290053_tif_M02

- profile: **danube**
- graphdig: 0.1.0
- input: `pages/290053_M02.png` (661x697)

## Panels

| panel | label | bbox (x,y,w,h) | conf | flags |
|---|---|---|---|---|
| p01 | M02 | 0,0,661,697 | 1.00 | seeded_from_annotations |

![panels](overlays/panels.png)

## Calibration

| panel | unit | scale | slope (unit/px) | r2 | ticks used | flags |
|---|---|---|---|---|---|---|
| p01 | bavarian_foot | linear | -0.010526 | 1.0000 | 2/2 | seeded_from_annotations |

## Extraction (lineformer_local)

| panel | candidates | selected | conf | coverage | s_alpha | method |
|---|---|---|---|---|---|---|
| p01 | 94 | 46 | 0.010 | 1.000 | 0.693 | qc_reselect_gemini_pick |

## Series

### p01
- csv: `series/p01.csv` (29 samples, 0 gaps, baseline off)
- confidence chain: panel=1.00, calibration=1.00, extraction=0.01, coverage=1.00
- QC: **major** The red curve traces a horizontal grid line on the left and right instead of following the actual data curve.

![curve](overlays/curve_p01.png)
![series](overlays/reconstruction_p01.png)

## Review flags

| severity | stage | panel | reason |
|---|---|---|---|
| info | qc | p01 | QC rejected candidate; reselected cand 46 |
| blocking | qc | p01 | major deviation persists: The red curve traces a horizontal grid line on the left and right instead of following the actual data curve. |
