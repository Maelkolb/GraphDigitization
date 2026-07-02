# Run report: 20260702-232423-TestGraph4

- profile: **generic**
- graphdig: 0.1.0
- input: `pages/TestGraph4.png` (1897x659)

## Panels

| panel | label | bbox (x,y,w,h) | conf | flags |
|---|---|---|---|---|
| p01 | Chart XVIII.—Pernicious anæmia. | 698,88,497,517 | 0.95 |  |

![panels](overlays/panels.png)

## Calibration

| panel | unit | scale | slope (unit/px) | r2 | ticks used | flags |
|---|---|---|---|---|---|---|
| p01 | unknown | linear | -13529 | 1.0000 | 6/6 | dual_axis:magnitude_split, dual_axis:right_scale_used |

## Extraction (lineformer_local)

| panel | candidates | selected | conf | coverage | s_alpha | method |
|---|---|---|---|---|---|---|
| p01 | 98 | 85 | 0.001 | 0.970 | 0.670 | qc_reselect_s_alpha |

## Series

### p01 (3 series)
- **RED CORPUSCLES** csv: `series/p01_s1.csv` (100 samples, 3 gaps, baseline off)
  - confidence chain: panel=0.95, calibration=1.00, extraction=0.00, coverage=0.97
  - QC: **major** The overlay starts on the lower curve, switches to the upper curve, and exhibits significant vertical offsets in several segments where it does not follow either line closely.
- **HAEMOGLOBIN** csv: `series/p01_s2.csv` (100 samples, 9 gaps, baseline off)
  - confidence chain: panel=0.95, calibration=1.00, extraction=0.86, coverage=0.91
  - QC: **ok** The extracted curve accurately tracks the lower data curve across the entire chart within one grid tick.
- **COLORLESS CORPUSCLES** csv: `series/p01_s3.csv` (100 samples, 3 gaps, baseline off)
  - confidence chain: panel=0.95, calibration=1.00, extraction=0.00, coverage=0.97
  - QC: **ok** The extracted curve follows the colorless corpuscles data line closely across the entire length of the chart.

![series](overlays/reconstruction_p01.png)

## Review flags

| severity | stage | panel | reason |
|---|---|---|---|
| info | triage |  | multi-series chart: 3 curves (RED CORPUSCLES, HAEMOGLOBIN, COLORLESS CORPUSCLES) |
| warning | series | p01_s1 | 6 empty slice(s): 1, 2, 3, 22, 23... |
| warning | series | p01_s2 | 9 empty slice(s): 1, 2, 3, 4, 5... |
| warning | series | p01_s3 | 3 empty slice(s): 88, 89, 90 |
| info | qc | p01_s1 | QC rejected candidate; reselected cand 85 |
| warning | series | p01_s1 | 3 empty slice(s): 1, 2, 3 |
| blocking | qc | p01_s1 | major deviation persists: The overlay starts on the lower curve, switches to the upper curve, and exhibits significant vertical offsets in several segments where it does not follow either line closely. |
| info | qc | p01_s3 | QC rejected candidate; reselected cand 31 |
| warning | series | p01_s3 | 3 empty slice(s): 2, 89, 90 |
