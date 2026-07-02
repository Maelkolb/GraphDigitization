# Run report: 20260702-111402-290022_tif_M06

- profile: **danube**
- graphdig: 0.1.0
- input: `pages/290022_M06.png` (663x523)

## Panels

| panel | label | bbox (x,y,w,h) | conf | flags |
|---|---|---|---|---|
| p01 | M06 | 0,0,663,523 | 1.00 | seeded_from_annotations |

![panels](overlays/panels.png)

## Calibration

| panel | unit | scale | slope (unit/px) | r2 | ticks used | flags |
|---|---|---|---|---|---|---|
| p01 | bavarian_foot | linear | -0.010526 | 1.0000 | 2/2 | seeded_from_annotations |

## Extraction (lineformer_local)

| panel | candidates | selected | conf | coverage | s_alpha | method |
|---|---|---|---|---|---|---|
| p01 | 99 | 1 | 0.917 | 1.000 | 0.974 | gemini_pick |

## Series

### p01
- csv: `series/p01.csv` (30 samples, 0 gaps, baseline off)
- confidence chain: panel=1.00, calibration=1.00, extraction=0.92, coverage=1.00
- QC: **ok** The red curve follows the hand-drawn data curve accurately within one grid tick across the entire segment.

![curve](overlays/curve_p01.png)
![series](overlays/series_p01.png)
