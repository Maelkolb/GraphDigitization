# Run report: 20260702-221526-290053_tif_M04

- profile: **danube**
- graphdig: 0.1.0
- input: `pages/290053_M04.png` (691x642)

## Panels

| panel | label | bbox (x,y,w,h) | conf | flags |
|---|---|---|---|---|
| p01 | M04 | 0,0,691,642 | 1.00 | seeded_from_annotations |

![panels](overlays/panels.png)

## Calibration

| panel | unit | scale | slope (unit/px) | r2 | ticks used | flags |
|---|---|---|---|---|---|---|
| p01 | mm | linear | -0.010526 | 1.0000 | 2/2 | seeded_from_annotations |

## Extraction (lineformer_local)

| panel | candidates | selected | conf | coverage | s_alpha | method |
|---|---|---|---|---|---|---|
| p01 | 99 | 0 | 0.930 | 1.000 | 0.978 | s_alpha |

## Series

### p01
- csv: `series/p01.csv` (30 samples, 0 gaps, baseline off)
- confidence chain: panel=1.00, calibration=1.00, extraction=0.93, coverage=1.00
- QC: **ok** The red curve follows the hand-drawn curve perfectly across the entire grid.

![curve](overlays/curve_p01.png)
![series](overlays/reconstruction_p01.png)
