# Run report: 20260702-221706-290053_tif_M12

- profile: **danube**
- graphdig: 0.1.0
- input: `pages/290053_M12.png` (703x361)

## Panels

| panel | label | bbox (x,y,w,h) | conf | flags |
|---|---|---|---|---|
| p01 | M12 | 0,0,703,361 | 1.00 | seeded_from_annotations |

![panels](overlays/panels.png)

## Calibration

| panel | unit | scale | slope (unit/px) | r2 | ticks used | flags |
|---|---|---|---|---|---|---|
| p01 | mm | linear | -0.010526 | 1.0000 | 2/2 | seeded_from_annotations |

## Extraction (lineformer_local)

| panel | candidates | selected | conf | coverage | s_alpha | method |
|---|---|---|---|---|---|---|
| p01 | 98 | 2 | 0.872 | 1.000 | 0.960 | gemini_pick |

## Series

### p01
- csv: `series/p01.csv` (31 samples, 0 gaps, baseline off)
- confidence chain: panel=1.00, calibration=1.00, extraction=0.87, coverage=1.00
- QC: **ok** The red curve closely tracks the hand-drawn line within one grid tick across the entire segment.

![curve](overlays/curve_p01.png)
![series](overlays/reconstruction_p01.png)
