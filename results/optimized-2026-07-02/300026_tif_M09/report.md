# Run report: 20260702-214703-300026_tif_M09

- profile: **danube**
- graphdig: 0.1.0
- input: `pages/300026_M09.png` (693x532)

## Panels

| panel | label | bbox (x,y,w,h) | conf | flags |
|---|---|---|---|---|
| p01 | M09 | 0,0,693,532 | 1.00 | seeded_from_annotations |

![panels](overlays/panels.png)

## Calibration

| panel | unit | scale | slope (unit/px) | r2 | ticks used | flags |
|---|---|---|---|---|---|---|
| p01 | bavarian_foot | linear | -0.010823 | 1.0000 | 2/2 | seeded_from_annotations |

## Extraction (lineformer_local)

| panel | candidates | selected | conf | coverage | s_alpha | method |
|---|---|---|---|---|---|---|
| p01 | 100 | 45 | 0.008 | 1.000 | 0.692 | qc_reselect_gemini_pick |

## Series

### p01
- csv: `series/p01.csv` (30 samples, 0 gaps, baseline off)
- confidence chain: panel=1.00, calibration=1.00, extraction=0.01, coverage=1.00
- QC: **major** The red curve is almost flat near the bottom and completely fails to follow the actual hand-drawn curve's shape and peaks.

![curve](overlays/curve_p01.png)
![series](overlays/reconstruction_p01.png)

## Review flags

| severity | stage | panel | reason |
|---|---|---|---|
| info | qc | p01 | QC rejected candidate; reselected cand 45 |
| blocking | qc | p01 | major deviation persists: The red curve is almost flat near the bottom and completely fails to follow the actual hand-drawn curve's shape and peaks. |
