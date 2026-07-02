# Run report: 20260702-221512-TestGraph5

- profile: **generic**
- graphdig: 0.1.0
- input: `pages/TestGraph5.png` (1897x659)

## Panels

| panel | label | bbox (x,y,w,h) | conf | flags |
|---|---|---|---|---|
| p01 | GRAPH C showing the course of SMALLPOX IN LONDON, 1902 (the last epidemic year of major smallpox) | 768,109,366,514 | 0.95 |  |

![panels](overlays/panels.png)

## Calibration

| panel | unit | scale | slope (unit/px) | r2 | ticks used | flags |
|---|---|---|---|---|---|---|
| p01 | unknown | linear | -3.5919 | 0.9922 | 74/74 | low_r2:0.9922, high_residual |

## Extraction (lineformer_local)

| panel | candidates | selected | conf | coverage | s_alpha | method |
|---|---|---|---|---|---|---|
| p01 | 97 | 0 | 0.873 | 0.790 | 0.816 | s_alpha |

## Series

### p01
- csv: `series/p01.csv` (100 samples, 21 gaps, baseline off)
- confidence chain: panel=0.95, calibration=0.98, extraction=0.87, coverage=0.79
- QC: **ok** The extracted curve tracks the upper line accurately with negligible deviations.

![curve](overlays/curve_p01.png)
![series](overlays/reconstruction_p01.png)

## Review flags

| severity | stage | panel | reason |
|---|---|---|---|
| warning | calibrate | p01 | axis fit r2=0.9922 below gate 0.995 |
| warning | calibrate | p01 | relative fit residual 0.027 above gate |
| warning | select | p01 | best candidate coverage 0.790 below viability gate 0.985 |
| warning | series | p01 | 21 empty slice(s): 69, 77, 78, 79, 80... |
