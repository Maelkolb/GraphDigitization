# Run report: 20260702-231814-210018_tif_M02

- profile: **danube**
- graphdig: 0.1.0
- input: `pages/210018_M02.png` (644x947)

## Panels

| panel | label | bbox (x,y,w,h) | conf | flags |
|---|---|---|---|---|
| p01 | M02 | 0,0,644,947 | 1.00 | seeded_from_annotations |

![panels](overlays/panels.png)

## Calibration

| panel | unit | scale | slope (unit/px) | r2 | ticks used | flags |
|---|---|---|---|---|---|---|
| p01 | bavarian_foot | linear | -0.010548 | 1.0000 | 2/2 | seeded_from_annotations |

## Extraction (lineformer_local)

| panel | candidates | selected | conf | coverage | s_alpha | method |
|---|---|---|---|---|---|---|
| p01 | 99 | 0 | 0.859 | 1.000 | 0.956 | s_alpha |

## Series

### p01
- csv: `series/p01.csv` (28 samples, 0 gaps, baseline off)
  - confidence chain: panel=1.00, calibration=1.00, extraction=0.86, coverage=1.00
  - QC: **minor** The extracted curve shows a minor vertical offset on the left and minor tracking noise near the steep peak.

![series](overlays/reconstruction_p01.png)

## Review flags

| severity | stage | panel | reason |
|---|---|---|---|
| warning | qc | p01 | minor deviation: The extracted curve shows a minor vertical offset on the left and minor tracking noise near the steep peak. |
