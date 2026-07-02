# Run report: 20260702-232542-TestGraph6

- profile: **generic**
- graphdig: 0.1.0
- input: `pages/TestGraph6.png` (1897x659)

## Panels

| panel | label | bbox (x,y,w,h) | conf | flags |
|---|---|---|---|---|
| p01 | Diagramm über die Leistung verschiedener Luftpumpen. | 598,142,669,510 | 1.00 |  |

![panels](overlays/panels.png)

## Calibration

| panel | unit | scale | slope (unit/px) | r2 | ticks used | flags |
|---|---|---|---|---|---|---|
| p01 | mm | log | 0.013751 | 1.0000 | 6/7 |  |

## Extraction (lineformer_local)

| panel | candidates | selected | conf | coverage | s_alpha | method |
|---|---|---|---|---|---|---|
| p01 | 99 | 1 | 0.843 | 0.905 | 0.886 | gemini_assign |

## Series

### p01 (3 series)
- **C Kapselpumpe mit Handbetrieb** csv: `series/p01_s1.csv` (21 samples, 2 gaps, baseline off)
  - confidence chain: panel=1.00, calibration=0.95, extraction=0.84, coverage=0.90
  - QC: **minor** The red curve follows curve C very closely but is missing the initial segment near the origin.
- **B Kapselpumpe mit Motorbetrieb** csv: `series/p01_s2.csv` (21 samples, 2 gaps, baseline off)
  - confidence chain: panel=1.00, calibration=0.95, extraction=0.01, coverage=0.90
  - QC: **major** The extracted curve incorrectly jumps from curve B to curve A near x=14 and follows it to the end.
- **A Geryk-Ölluftpumpe mit Schwungrad** csv: `series/p01_s3.csv` (21 samples, 2 gaps, baseline off)
  - confidence chain: panel=1.00, calibration=0.95, extraction=0.00, coverage=0.90
  - QC: **major** The red curve exhibits severe noise and jagged spikes in the middle section instead of smoothly following curve 'a'.

![series](overlays/reconstruction_p01.png)

## Review flags

| severity | stage | panel | reason |
|---|---|---|---|
| info | triage |  | multi-series chart: 3 curves (A Geryk-Ölluftpumpe mit Schwungrad, B Kapselpumpe mit Motorbetrieb, C Kapselpumpe mit Handbetrieb) |
| warning | series | p01_s1 | 2 empty slice(s): 19, 20 |
| warning | series | p01_s2 | 2 empty slice(s): 19, 20 |
| warning | series | p01_s3 | 2 empty slice(s): 19, 20 |
| warning | qc | p01_s1 | minor deviation: The red curve follows curve C very closely but is missing the initial segment near the origin. |
| info | qc | p01_s2 | QC rejected candidate; reselected cand 18 |
| warning | series | p01_s2 | 2 empty slice(s): 19, 20 |
| blocking | qc | p01_s2 | major deviation persists: The extracted curve incorrectly jumps from curve B to curve A near x=14 and follows it to the end. |
| info | qc | p01_s3 | QC rejected candidate; reselected cand 75 |
| warning | series | p01_s3 | 2 empty slice(s): 19, 20 |
| blocking | qc | p01_s3 | major deviation persists: The red curve exhibits severe noise and jagged spikes in the middle section instead of smoothly following curve 'a'. |
