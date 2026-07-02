# Run report: 20260702-221512-290053_tif_M03

- profile: **danube**
- graphdig: 0.1.0
- input: `pages/290053_M03.png` (702x661)

## Panels

| panel | label | bbox (x,y,w,h) | conf | flags |
|---|---|---|---|---|
| p01 | M03 | 0,0,702,661 | 1.00 | seeded_from_annotations |

![panels](overlays/panels.png)

## Calibration

| panel | unit | scale | slope (unit/px) | r2 | ticks used | flags |
|---|---|---|---|---|---|---|
| p01 | bavarian_foot | linear | -0.010526 | 1.0000 | 2/2 | seeded_from_annotations |

## Extraction (lineformer_local)

| panel | candidates | selected | conf | coverage | s_alpha | method |
|---|---|---|---|---|---|---|
| p01 | 99 | 1 | 0.889 | 1.000 | 0.966 | gemini_pick |

## Series

### p01
- csv: `series/p01.csv` (31 samples, 0 gaps, baseline off)
- confidence chain: panel=1.00, calibration=1.00, extraction=0.89, coverage=1.00
- QC: **minor** The red overlay exhibits a minor vertical offset, running slightly above the actual line along the flatter right-hand section.

![curve](overlays/curve_p01.png)
![series](overlays/reconstruction_p01.png)

## Review flags

| severity | stage | panel | reason |
|---|---|---|---|
| warning | qc | p01 | minor deviation: The red overlay exhibits a minor vertical offset, running slightly above the actual line along the flatter right-hand section. |
