# Run report: 20260702-232143-TestGraph3

- profile: **generic**
- graphdig: 0.1.0
- input: `pages/TestGraph3.png` (1897x659)

## Panels

| panel | label | bbox (x,y,w,h) | conf | flags |
|---|---|---|---|---|
| p01 | Antalet åtal mot barn och ungdom i Köbenh. | 607,46,660,587 | 1.00 |  |

![panels](overlays/panels.png)

## Calibration

| panel | unit | scale | slope (unit/px) | r2 | ticks used | flags |
|---|---|---|---|---|---|---|
| p01 | unknown | linear | -1.2955 | 1.0000 | 5/6 |  |

## Extraction (lineformer_local)

| panel | candidates | selected | conf | coverage | s_alpha | method |
|---|---|---|---|---|---|---|
| p01 | 99 | 1 | 0.914 | 1.000 | 0.973 | gemini_assign |

## Series

### p01 (2 series)
- **14-18 åringar.** csv: `series/p01_s1.csv` (100 samples, 0 gaps, baseline off)
  - confidence chain: panel=1.00, calibration=1.00, extraction=0.91, coverage=1.00
  - QC: **ok** The extracted curve follows the solid line representing the 14-18 years group with high precision throughout the entire chart.
- **under 14 år.** csv: `series/p01_s2.csv` (100 samples, 0 gaps, baseline off)
  - confidence chain: panel=1.00, calibration=1.00, extraction=0.93, coverage=1.00
  - QC: **major** The extracted curve tracks along the absolute bottom margin of the image instead of following the dashed line representing 'under 14 år'.

![series](overlays/reconstruction_p01.png)

## Review flags

| severity | stage | panel | reason |
|---|---|---|---|
| info | triage |  | multi-series chart: 2 curves (14-18 åringar., under 14 år.) |
| info | qc | p01_s2 | QC rejected candidate; reselected cand 0 |
| blocking | qc | p01_s2 | major deviation persists: The extracted curve tracks along the absolute bottom margin of the image instead of following the dashed line representing 'under 14 år'. |
