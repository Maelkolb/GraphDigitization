# Run report: 20260702-221626-290053_tif_M09

- profile: **danube**
- graphdig: 0.1.0
- input: `pages/290053_M09.png` (680x449)

## Panels

| panel | label | bbox (x,y,w,h) | conf | flags |
|---|---|---|---|---|
| p01 | M09 | 0,0,680,449 | 1.00 | seeded_from_annotations |

![panels](overlays/panels.png)

## Calibration

| panel | unit | scale | slope (unit/px) | r2 | ticks used | flags |
|---|---|---|---|---|---|---|
| p01 | mm | linear | -0.010526 | 1.0000 | 2/2 | seeded_from_annotations |

## Extraction (lineformer_local)

| panel | candidates | selected | conf | coverage | s_alpha | method |
|---|---|---|---|---|---|---|
| p01 | 100 | 0 | 0.919 | 1.000 | 0.975 | s_alpha |

## Series

### p01
- csv: `series/p01.csv` (30 samples, 0 gaps, baseline off)
- confidence chain: panel=1.00, calibration=1.00, extraction=0.92, coverage=1.00
- QC: **ok** The extracted red curve accurately traces the upper boundary of the blue shaded line across the entire tile with no noticeable deviations.

![curve](overlays/curve_p01.png)
![series](overlays/reconstruction_p01.png)
