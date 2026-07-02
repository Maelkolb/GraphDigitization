# Run report: 20260702-221347-210051_tif_M09

- profile: **danube**
- graphdig: 0.1.0
- input: `pages/210051_M09.png` (678x268)

## Panels

| panel | label | bbox (x,y,w,h) | conf | flags |
|---|---|---|---|---|
| p01 | M09 | 0,0,678,268 | 1.00 | seeded_from_annotations |

![panels](overlays/panels.png)

## Calibration

| panel | unit | scale | slope (unit/px) | r2 | ticks used | flags |
|---|---|---|---|---|---|---|
| p01 | bavarian_foot | linear | -0.010782 | 1.0000 | 2/2 | seeded_from_annotations |

## Extraction (lineformer_local)

| panel | candidates | selected | conf | coverage | s_alpha | method |
|---|---|---|---|---|---|---|
| p01 | 100 | 0 | 0.912 | 1.000 | 0.973 | s_alpha |

## Series

### p01
- csv: `series/p01.csv` (30 samples, 0 gaps, baseline off)
- confidence chain: panel=1.00, calibration=1.00, extraction=0.91, coverage=1.00
- QC: **ok** The red curve aligns perfectly with the blue hand-drawn line across the entire image.

![curve](overlays/curve_p01.png)
![series](overlays/reconstruction_p01.png)
