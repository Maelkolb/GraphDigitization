# Run report: 20260702-221402-210051_tif_M10

- profile: **danube**
- graphdig: 0.1.0
- input: `pages/210051_M10.png` (709x472)

## Panels

| panel | label | bbox (x,y,w,h) | conf | flags |
|---|---|---|---|---|
| p01 | M10 | 0,0,709,472 | 1.00 | seeded_from_annotations |

![panels](overlays/panels.png)

## Calibration

| panel | unit | scale | slope (unit/px) | r2 | ticks used | flags |
|---|---|---|---|---|---|---|
| p01 | bavarian_foot | linear | -0.010782 | 1.0000 | 2/2 | seeded_from_annotations |

## Extraction (lineformer_local)

| panel | candidates | selected | conf | coverage | s_alpha | method |
|---|---|---|---|---|---|---|
| p01 | 100 | 2 | 0.716 | 1.000 | 0.912 | gemini_pick |

## Series

### p01
- csv: `series/p01.csv` (31 samples, 0 gaps, baseline off)
- confidence chain: panel=1.00, calibration=1.00, extraction=0.72, coverage=1.00
- QC: **ok** The red curve closely tracks the top edge of the blue curve within one grid tick throughout.

![curve](overlays/curve_p01.png)
![series](overlays/reconstruction_p01.png)
