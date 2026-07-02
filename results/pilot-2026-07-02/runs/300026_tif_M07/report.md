# Run report: 20260702-031152-300026_tif_M07

- profile: **danube**
- graphdig: 0.1.0
- input: `pages/300026_M07.png` (721x831)

## Panels

| panel | label | bbox (x,y,w,h) | conf | flags |
|---|---|---|---|---|
| p01 | M07 | 0,0,721,831 | 1.00 | seeded_from_annotations |

![panels](overlays/panels.png)

## Calibration

| panel | unit | scale | slope (unit/px) | r2 | ticks used | flags |
|---|---|---|---|---|---|---|
| p01 | bavarian_foot | linear | -0.010823 | 1.0000 | 2/2 | seeded_from_annotations |

## Extraction (lineformer_local)

| panel | candidates | selected | conf | coverage | s_alpha | method |
|---|---|---|---|---|---|---|
| p01 | 91 | 0 | 0.821 | 0.742 | 0.766 | s_alpha |

## Series

### p01
- csv: `series/p01.csv` (31 samples, 8 gaps, baseline off)
- confidence chain: panel=1.00, calibration=1.00, extraction=0.82, coverage=0.74

![curve](overlays/curve_p01.png)
![series](overlays/series_p01.png)

## Review flags

| severity | stage | panel | reason |
|---|---|---|---|
| warning | select | p01 | best candidate coverage 0.742 below viability gate 0.985 |
| warning | series | p01 | 8 empty slice(s): 1848-07-01, 1848-07-02, 1848-07-03, 1848-07-04, 1848-07-05... |
| info | qc |  | skipped: No GEMINI_API_KEY / GOOGLE_API_KEY found. Copy .env.example to .env and add your key, or export it in the environment. |
