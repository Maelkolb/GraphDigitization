# Run report: 20260702-221335-210051_tif_M08

- profile: **danube**
- graphdig: 0.1.0
- input: `pages/210051_M08.png` (690x323)

## Panels

| panel | label | bbox (x,y,w,h) | conf | flags |
|---|---|---|---|---|
| p01 | M08 | 0,0,690,323 | 1.00 | seeded_from_annotations |

![panels](overlays/panels.png)

## Calibration

| panel | unit | scale | slope (unit/px) | r2 | ticks used | flags |
|---|---|---|---|---|---|---|
| p01 | bavarian_foot | linear | -0.010782 | 1.0000 | 2/2 | seeded_from_annotations |

## Extraction (lineformer_local)

| panel | candidates | selected | conf | coverage | s_alpha | method |
|---|---|---|---|---|---|---|
| p01 | 100 | 7 | 0.108 | 1.000 | 0.723 | gemini_pick |

## Series

### p01
- csv: `series/p01.csv` (31 samples, 0 gaps, baseline off)
- confidence chain: panel=1.00, calibration=1.00, extraction=0.11, coverage=1.00
- QC: **ok** The red curve matches the hand-drawn blue curve accurately throughout.

![curve](overlays/curve_p01.png)
![series](overlays/reconstruction_p01.png)
