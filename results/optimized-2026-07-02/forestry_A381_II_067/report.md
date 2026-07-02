# Run report: 20260702-214550-forestry_A381_II_067

- profile: **generic**
- graphdig: 0.1.0
- input: `pages/forestry_A381_II_067.png` (1652x1362)

## Panels

| panel | label | bbox (x,y,w,h) | conf | flags |
|---|---|---|---|---|
| p01 | Fichten zur Probeflaeche N. 1. | 46,123,1366,612 | 0.95 |  |
| p02 | Fichten zur Probeflaeche N. 14. Klingenbrunn | 88,838,1343,490 | 0.95 |  |

![panels](overlays/panels.png)

## Calibration

| panel | unit | scale | slope (unit/px) | r2 | ticks used | flags |
|---|---|---|---|---|---|---|
| p01 | bavarian_zoll | linear | -0.52632 | 0.9987 | 28/28 | curve_labels |
| p02 | bavarian_zoll | linear | -0.46138 | 0.9935 | 21/21 | curve_labels, low_r2:0.9935, high_residual |

## Extraction (lineformer_local)

| panel | candidates | selected | conf | coverage | s_alpha | method |
|---|---|---|---|---|---|---|
| p01 | 94 | 90 | 0.005 | 0.750 | 0.519 | s_alpha |
| p02 | 35 | 26 | 0.006 | 0.380 | 0.264 | s_alpha |

## Series

### p01
- csv: `series/p01.csv` (100 samples, 25 gaps, baseline off)
- confidence chain: panel=0.95, calibration=1.00, extraction=0.00, coverage=0.75
- QC: **major** The digitized red curve deviates significantly from the smooth hand-drawn curve, exhibiting erratic spikes and drops to the baseline in the lower half.

![curve](overlays/curve_p01.png)
![series](overlays/reconstruction_p01.png)

### p02
- csv: `series/p02.csv` (100 samples, 62 gaps, baseline off)
- confidence chain: panel=0.95, calibration=0.95, extraction=0.01, coverage=0.38
- QC: **major** The extracted red curve has a large, artificial vertical spike near the center fold of the page that is not present on the original smooth curve.

![curve](overlays/curve_p02.png)
![series](overlays/reconstruction_p02.png)

## Review flags

| severity | stage | panel | reason |
|---|---|---|---|
| warning | calibrate | p02 | axis fit r2=0.9935 below gate 0.995 |
| warning | calibrate | p02 | relative fit residual 0.025 above gate |
| warning | select | p01 | best candidate coverage 0.750 below viability gate 0.985 |
| warning | select | p02 | best candidate coverage 0.380 below viability gate 0.985 |
| warning | series | p01 | 25 empty slice(s): 1, 2, 3, 4, 5... |
| warning | series | p02 | 62 empty slice(s): 1, 2, 3, 4, 5... |
| blocking | qc | p01 | major verdict but no alternative candidate left |
| blocking | qc | p01 | major deviation persists: The digitized red curve deviates significantly from the smooth hand-drawn curve, exhibiting erratic spikes and drops to the baseline in the lower half. |
| blocking | qc | p02 | major verdict but no alternative candidate left |
| blocking | qc | p02 | major deviation persists: The extracted red curve has a large, artificial vertical spike near the center fold of the page that is not present on the original smooth curve. |
