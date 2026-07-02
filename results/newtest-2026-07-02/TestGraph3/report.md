# Run report: 20260702-221226-TestGraph3

- profile: **generic**
- graphdig: 0.1.0
- input: `pages/TestGraph3.png` (1897x659)

## Panels

| panel | label | bbox (x,y,w,h) | conf | flags |
|---|---|---|---|---|
| p01 | Antalet åtal mot barn och ungdom i Köbenh. | 603,45,668,584 | 1.00 |  |

![panels](overlays/panels.png)

## Calibration

| panel | unit | scale | slope (unit/px) | r2 | ticks used | flags |
|---|---|---|---|---|---|---|
| p01 | unknown | linear | -1.2832 | 1.0000 | 6/6 |  |

## Extraction (lineformer_local)

| panel | candidates | selected | conf | coverage | s_alpha | method |
|---|---|---|---|---|---|---|
| p01 | 95 | 1 | 0.912 | 1.000 | 0.973 | gemini_pick |

## Series

### p01
- csv: `series/p01.csv` (100 samples, 0 gaps, baseline off)
- confidence chain: panel=1.00, calibration=0.98, extraction=0.91, coverage=1.00
- QC: **minor** The overlay tracks the top solid curve well but includes an incorrect vertical segment along the left border.

![curve](overlays/curve_p01.png)
![series](overlays/reconstruction_p01.png)

## Review flags

| severity | stage | panel | reason |
|---|---|---|---|
| warning | qc | p01 | minor deviation: The overlay tracks the top solid curve well but includes an incorrect vertical segment along the left border. |
