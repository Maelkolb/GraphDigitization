# Run report: 20260702-221431-TestGraph4

- profile: **generic**
- graphdig: 0.1.0
- input: `pages/TestGraph4.png` (1897x659)

## Panels

| panel | label | bbox (x,y,w,h) | conf | flags |
|---|---|---|---|---|
| p01 | Chart XVIII.—Pernicious anæmia. | 692,88,522,515 | 1.00 |  |

![panels](overlays/panels.png)

## Calibration

| panel | unit | scale | slope (unit/px) | r2 | ticks used | flags |
|---|---|---|---|---|---|---|
| p01 | unknown | linear | 9.9285 | 0.3656 | 15/15 | low_r2:0.3656, high_residual |

## Extraction (lineformer_local)

| panel | candidates | selected | conf | coverage | s_alpha | method |
|---|---|---|---|---|---|---|
| p01 | 98 | 0 | 0.899 | 0.960 | 0.941 | s_alpha |

## Series

### p01
- csv: `series/p01.csv` (100 samples, 4 gaps, baseline off)
- confidence chain: panel=1.00, calibration=0.95, extraction=0.90, coverage=0.96
- QC: **minor** The tracking starts on the lower curve before transitioning to the upper curve at the beginning.

![curve](overlays/curve_p01.png)
![series](overlays/reconstruction_p01.png)

## Review flags

| severity | stage | panel | reason |
|---|---|---|---|
| warning | calibrate | p01 | axis fit r2=0.3656 below gate 0.995 |
| warning | calibrate | p01 | relative fit residual 0.246 above gate |
| warning | select | p01 | best candidate coverage 0.960 below viability gate 0.985 |
| warning | series | p01 | 4 empty slice(s): 1, 2, 3, 4 |
| warning | qc | p01 | minor deviation: The tracking starts on the lower curve before transitioning to the upper curve at the beginning. |
