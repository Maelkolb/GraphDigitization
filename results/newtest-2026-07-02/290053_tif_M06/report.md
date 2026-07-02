# Run report: 20260702-221547-290053_tif_M06

- profile: **danube**
- graphdig: 0.1.0
- input: `pages/290053_M06.png` (672x605)

## Panels

| panel | label | bbox (x,y,w,h) | conf | flags |
|---|---|---|---|---|
| p01 | M06 | 0,0,672,605 | 1.00 | seeded_from_annotations |

![panels](overlays/panels.png)

## Calibration

| panel | unit | scale | slope (unit/px) | r2 | ticks used | flags |
|---|---|---|---|---|---|---|
| p01 | mm | linear | -0.010526 | 1.0000 | 2/2 | seeded_from_annotations |

## Extraction (lineformer_local)

| panel | candidates | selected | conf | coverage | s_alpha | method |
|---|---|---|---|---|---|---|
| p01 | 91 | 0 | 0.912 | 1.000 | 0.973 | s_alpha |

## Series

### p01
- csv: `series/p01.csv` (30 samples, 0 gaps, baseline off)
- confidence chain: panel=1.00, calibration=1.00, extraction=0.91, coverage=1.00
- QC: **ok** The red curve precisely tracks the dark hand-drawn line across the entire grid segment.

![curve](overlays/curve_p01.png)
![series](overlays/reconstruction_p01.png)
