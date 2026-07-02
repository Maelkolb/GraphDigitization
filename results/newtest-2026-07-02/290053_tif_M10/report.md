# Run report: 20260702-221636-290053_tif_M10

- profile: **danube**
- graphdig: 0.1.0
- input: `pages/290053_M10.png` (696x434)

## Panels

| panel | label | bbox (x,y,w,h) | conf | flags |
|---|---|---|---|---|
| p01 | M10 | 0,0,696,434 | 1.00 | seeded_from_annotations |

![panels](overlays/panels.png)

## Calibration

| panel | unit | scale | slope (unit/px) | r2 | ticks used | flags |
|---|---|---|---|---|---|---|
| p01 | mm | linear | -0.010526 | 1.0000 | 2/2 | seeded_from_annotations |

## Extraction (lineformer_local)

| panel | candidates | selected | conf | coverage | s_alpha | method |
|---|---|---|---|---|---|---|
| p01 | 100 | 3 | 0.661 | 1.000 | 0.895 | gemini_pick |

## Series

### p01
- csv: `series/p01.csv` (31 samples, 0 gaps, baseline off)
- confidence chain: panel=1.00, calibration=1.00, extraction=0.66, coverage=1.00
- QC: **ok** The extracted red curve accurately follows the hand-drawn dark blue line across the entire image.

![curve](overlays/curve_p01.png)
![series](overlays/reconstruction_p01.png)
