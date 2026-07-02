# Run report: 20260702-221444-210051_tif_M12

- profile: **danube**
- graphdig: 0.1.0
- input: `pages/210051_M12.png` (700x270)

## Panels

| panel | label | bbox (x,y,w,h) | conf | flags |
|---|---|---|---|---|
| p01 | M12 | 0,0,700,270 | 1.00 | seeded_from_annotations |

![panels](overlays/panels.png)

## Calibration

| panel | unit | scale | slope (unit/px) | r2 | ticks used | flags |
|---|---|---|---|---|---|---|
| p01 | bavarian_foot | linear | -0.010782 | 1.0000 | 2/2 | seeded_from_annotations |

## Extraction (lineformer_local)

| panel | candidates | selected | conf | coverage | s_alpha | method |
|---|---|---|---|---|---|---|
| p01 | 100 | 9 | 0.047 | 1.000 | 0.705 | gemini_pick |

## Series

### p01
- csv: `series/p01.csv` (31 samples, 0 gaps, baseline off)
- confidence chain: panel=1.00, calibration=1.00, extraction=0.05, coverage=1.00
- QC: **ok** The red curve accurately tracks the dark blue upper boundary of the line across the entire chart within one grid tick.

![curve](overlays/curve_p01.png)
![series](overlays/reconstruction_p01.png)
