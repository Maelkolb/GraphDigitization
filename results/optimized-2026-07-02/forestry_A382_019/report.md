# Run report: 20260702-214940-forestry_A382_019

- profile: **generic**
- graphdig: 0.1.0
- input: `pages/forestry_A382_019.png` (1652x974)

## Panels

| panel | label | bbox (x,y,w,h) | conf | flags |
|---|---|---|---|---|
| p01 | Fichten
VII.4.a. | 56,99,908,760 | 1.00 |  |
| p02 | Tannen
VII.4.a. | 56,851,908,743 | 1.00 |  |

![panels](overlays/panels.png)

## Calibration

| panel | unit | scale | slope (unit/px) | r2 | ticks used | flags |
|---|---|---|---|---|---|---|
| p01 | unknown | linear | -0.18983 | 0.9999 | 26/26 |  |
| p02 | unknown | linear | -0.1872 | 1.0000 | 26/26 |  |

## Extraction (lineformer_local)

| panel | candidates | selected | conf | coverage | s_alpha | method |
|---|---|---|---|---|---|---|
| p01 | 72 | 0 | 0.908 | 0.840 | 0.861 | s_alpha |
| p02 | 99 | 0 | 0.901 | 0.910 | 0.907 | s_alpha |

## Series

### p01
- csv: `series/p01.csv` (100 samples, 16 gaps, baseline off)
- confidence chain: panel=1.00, calibration=0.95, extraction=0.91, coverage=0.84
- QC: **ok** The extracted curve follows the hand-drawn trend line accurately across the entire grid, correctly ignoring the surrounding scatter points.

![curve](overlays/curve_p01.png)
![series](overlays/reconstruction_p01.png)

### p02
- csv: `series/p02.csv` (100 samples, 9 gaps, baseline off)
- confidence chain: panel=1.00, calibration=0.95, extraction=0.90, coverage=0.91
- QC: **minor** The extracted curve shows a slight vertical deviation, running just above the original drawn line through the middle section.

![curve](overlays/curve_p02.png)
![series](overlays/reconstruction_p02.png)

## Review flags

| severity | stage | panel | reason |
|---|---|---|---|
| warning | select | p01 | best candidate coverage 0.840 below viability gate 0.985 |
| warning | select | p02 | best candidate coverage 0.910 below viability gate 0.985 |
| warning | series | p01 | 16 empty slice(s): 1, 2, 3, 4, 5... |
| warning | series | p02 | 9 empty slice(s): 2, 3, 4, 5, 6... |
| warning | qc | p02 | minor deviation: The extracted curve shows a slight vertical deviation, running just above the original drawn line through the middle section. |
