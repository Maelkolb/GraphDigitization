# Run report: 20260702-221558-290053_tif_M07

- profile: **danube**
- graphdig: 0.1.0
- input: `pages/290053_M07.png` (711x498)

## Panels

| panel | label | bbox (x,y,w,h) | conf | flags |
|---|---|---|---|---|
| p01 | M07 | 0,0,711,498 | 1.00 | seeded_from_annotations |

![panels](overlays/panels.png)

## Calibration

| panel | unit | scale | slope (unit/px) | r2 | ticks used | flags |
|---|---|---|---|---|---|---|
| p01 | mm | linear | -0.010526 | 1.0000 | 2/2 | seeded_from_annotations |

## Extraction (lineformer_local)

| panel | candidates | selected | conf | coverage | s_alpha | method |
|---|---|---|---|---|---|---|
| p01 | 100 | 4 | 0.277 | 1.000 | 0.776 | gemini_pick |

## Series

### p01
- csv: `series/p01.csv` (31 samples, 0 gaps, baseline off)
- confidence chain: panel=1.00, calibration=1.00, extraction=0.28, coverage=1.00
- QC: **ok** The red curve accurately follows the upper dark blue outline of the data ribbon with high precision.

![curve](overlays/curve_p01.png)
![series](overlays/reconstruction_p01.png)
