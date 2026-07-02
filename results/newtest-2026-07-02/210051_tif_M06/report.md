# Run report: 20260702-221301-210051_tif_M06

- profile: **danube**
- graphdig: 0.1.0
- input: `pages/210051_M06.png` (675x468)

## Panels

| panel | label | bbox (x,y,w,h) | conf | flags |
|---|---|---|---|---|
| p01 | M06 | 0,0,675,468 | 1.00 | seeded_from_annotations |

![panels](overlays/panels.png)

## Calibration

| panel | unit | scale | slope (unit/px) | r2 | ticks used | flags |
|---|---|---|---|---|---|---|
| p01 | bavarian_foot | linear | -0.010782 | 1.0000 | 2/2 | seeded_from_annotations |

## Extraction (lineformer_local)

| panel | candidates | selected | conf | coverage | s_alpha | method |
|---|---|---|---|---|---|---|
| p01 | 100 | 1 | 0.899 | 1.000 | 0.969 | s_alpha |

## Series

### p01
- csv: `series/p01.csv` (30 samples, 0 gaps, baseline off)
- confidence chain: panel=1.00, calibration=1.00, extraction=0.90, coverage=1.00
- QC: **minor** The extracted curve slightly cuts below the two sharpest peaks towards the right.

![curve](overlays/curve_p01.png)
![series](overlays/reconstruction_p01.png)

## Review flags

| severity | stage | panel | reason |
|---|---|---|---|
| warning | qc | p01 | minor deviation: The extracted curve slightly cuts below the two sharpest peaks towards the right. |
