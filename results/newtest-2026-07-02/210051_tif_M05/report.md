# Run report: 20260702-221244-210051_tif_M05

- profile: **danube**
- graphdig: 0.1.0
- input: `pages/210051_M05.png` (696x573)

## Panels

| panel | label | bbox (x,y,w,h) | conf | flags |
|---|---|---|---|---|
| p01 | M05 | 0,0,696,573 | 1.00 | seeded_from_annotations |

![panels](overlays/panels.png)

## Calibration

| panel | unit | scale | slope (unit/px) | r2 | ticks used | flags |
|---|---|---|---|---|---|---|
| p01 | bavarian_foot | linear | -0.010782 | 1.0000 | 2/2 | seeded_from_annotations |

## Extraction (lineformer_local)

| panel | candidates | selected | conf | coverage | s_alpha | method |
|---|---|---|---|---|---|---|
| p01 | 98 | 15 | 0.020 | 1.000 | 0.696 | gemini_pick |

## Series

### p01
- csv: `series/p01.csv` (31 samples, 0 gaps, baseline off)
- confidence chain: panel=1.00, calibration=1.00, extraction=0.02, coverage=1.00
- QC: **minor** The red curve follows the general path well but exhibits minor vertical offsets from the center of the drawn line in several segments.

![curve](overlays/curve_p01.png)
![series](overlays/reconstruction_p01.png)

## Review flags

| severity | stage | panel | reason |
|---|---|---|---|
| warning | qc | p01 | minor deviation: The red curve follows the general path well but exhibits minor vertical offsets from the center of the drawn line in several segments. |
