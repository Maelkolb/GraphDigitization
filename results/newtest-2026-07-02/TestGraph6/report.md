# Run report: 20260702-221628-TestGraph6

- profile: **generic**
- graphdig: 0.1.0
- input: `pages/TestGraph6.png` (1897x659)

## Panels

| panel | label | bbox (x,y,w,h) | conf | flags |
|---|---|---|---|---|
| p01 | Diagramm über die Leistung verschiedener Luftpumpen. | 598,155,664,501 | 1.00 |  |

![panels](overlays/panels.png)

## Calibration

| panel | unit | scale | slope (unit/px) | r2 | ticks used | flags |
|---|---|---|---|---|---|---|
| p01 | mm | log | 0.013498 | 0.9999 | 7/7 |  |

## Extraction (lineformer_local)

| panel | candidates | selected | conf | coverage | s_alpha | method |
|---|---|---|---|---|---|---|
| p01 | 99 | 82 | 0.002 | 1.000 | 0.691 | qc_reselect_s_alpha |

## Series

### p01
- csv: `series/p01.csv` (21 samples, 0 gaps, baseline off)
- confidence chain: panel=1.00, calibration=0.95, extraction=0.00, coverage=1.00
- QC: **major** The red curve diverges significantly from the smooth curve 'a', tracking background grid lines and noise instead.

![curve](overlays/curve_p01.png)
![series](overlays/reconstruction_p01.png)

## Review flags

| severity | stage | panel | reason |
|---|---|---|---|
| info | qc | p01 | QC rejected candidate; reselected cand 82 |
| blocking | qc | p01 | major deviation persists: The red curve diverges significantly from the smooth curve 'a', tracking background grid lines and noise instead. |
