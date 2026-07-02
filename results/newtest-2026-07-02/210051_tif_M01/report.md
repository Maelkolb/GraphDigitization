# Run report: 20260702-221139-210051_tif_M01

- profile: **danube**
- graphdig: 0.1.0
- input: `pages/210051_M01.png` (709x382)

## Panels

| panel | label | bbox (x,y,w,h) | conf | flags |
|---|---|---|---|---|
| p01 | M01 | 0,0,709,382 | 1.00 | seeded_from_annotations |

![panels](overlays/panels.png)

## Calibration

| panel | unit | scale | slope (unit/px) | r2 | ticks used | flags |
|---|---|---|---|---|---|---|
| p01 | bavarian_foot | linear | -0.010782 | 1.0000 | 2/2 | seeded_from_annotations |

## Extraction (lineformer_local)

| panel | candidates | selected | conf | coverage | s_alpha | method |
|---|---|---|---|---|---|---|
| p01 | 100 | 0 | 0.885 | 1.000 | 0.964 | s_alpha |

## Series

### p01
- csv: `series/p01.csv` (31 samples, 0 gaps, baseline off)
- confidence chain: panel=1.00, calibration=1.00, extraction=0.89, coverage=1.00
- QC: **ok** The red curve tracks the original hand-drawn curve very accurately with only negligible deviations.

![curve](overlays/curve_p01.png)
![series](overlays/reconstruction_p01.png)
