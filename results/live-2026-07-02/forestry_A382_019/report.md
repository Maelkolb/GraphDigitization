# Run report: 20260702-111359-forestry_A382_019

- profile: **generic**
- graphdig: 0.1.0
- input: `pages/forestry_A382_019.png` (1652x974)

## Panels

| panel | label | bbox (x,y,w,h) | conf | flags |
|---|---|---|---|---|
| p01 | Tannen
VII. Cl. | 10,58,901,751 | 1.00 |  |
| p02 | Fichten
VII. Cl. | 10,809,901,760 | 1.00 |  |

![panels](overlays/panels.png)

## Calibration

| panel | unit | scale | slope (unit/px) | r2 | ticks used | flags |
|---|---|---|---|---|---|---|
| p01 | H | linear | 0.19596 | 1.0000 | 26/26 |  |
| p02 | unknown | linear | 0.20218 | 1.0000 | 29/29 |  |

## Extraction (lineformer_local)

| panel | candidates | selected | conf | coverage | s_alpha | method |
|---|---|---|---|---|---|---|
| p01 | 87 | 2 | 0.851 | 0.970 | 0.933 | s_alpha |
| p02 | 95 | 0 | 0.701 | 0.630 | 0.652 | s_alpha |

## Series

### p01
- csv: `series/p01.csv` (100 samples, 3 gaps, baseline off)
- confidence chain: panel=1.00, calibration=1.00, extraction=0.85, coverage=0.97
- QC: **minor** The extracted curve shows minor vertical deviation and noise, particularly on the left half where it stays slightly above the hand-drawn line.

![curve](overlays/curve_p01.png)
![series](overlays/series_p01.png)

### p02
- csv: `series/p02.csv` (100 samples, 37 gaps, baseline off)
- confidence chain: panel=1.00, calibration=0.98, extraction=0.70, coverage=0.63
- QC: **minor** The overlay is missing the initial segment of the curve on the left, but otherwise follows the drawn line accurately.

![curve](overlays/curve_p02.png)
![series](overlays/series_p02.png)

## Review flags

| severity | stage | panel | reason |
|---|---|---|---|
| warning | select | p01 | best candidate coverage 0.970 below viability gate 0.985 |
| warning | select | p02 | best candidate coverage 0.630 below viability gate 0.985 |
| warning | series | p01 | 3 empty slice(s): 33.3131, 0.343434, 0 |
| warning | series | p02 | 37 empty slice(s): 30, 29.697, 29.3939, 29.0909, 28.7879... |
| warning | qc | p01 | minor deviation: The extracted curve shows minor vertical deviation and noise, particularly on the left half where it stays slightly above the hand-drawn line. |
| warning | qc | p02 | minor deviation: The overlay is missing the initial segment of the curve on the left, but otherwise follows the drawn line accurately. |
