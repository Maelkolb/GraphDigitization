# Run report: 20260702-031015-290022_tif_M01

- profile: **danube**
- graphdig: 0.1.0
- input: `pages/290022_M01.png` (730x1245)

## Panels

| panel | label | bbox (x,y,w,h) | conf | flags |
|---|---|---|---|---|
| p01 | M01 | 0,0,730,1245 | 1.00 | seeded_from_annotations |

![panels](overlays/panels.png)

## Calibration

| panel | unit | scale | slope (unit/px) | r2 | ticks used | flags |
|---|---|---|---|---|---|---|
| p01 | bavarian_foot | linear | -0.010526 | 1.0000 | 2/2 | seeded_from_annotations |

## Extraction (lineformer_local)

| panel | candidates | selected | conf | coverage | s_alpha | method |
|---|---|---|---|---|---|---|
| p01 | 99 | 0 | 0.869 | 0.742 | 0.781 | s_alpha |

## Series

### p01
- csv: `series/p01.csv` (31 samples, 8 gaps, baseline off)
- confidence chain: panel=1.00, calibration=1.00, extraction=0.87, coverage=0.74

![curve](overlays/curve_p01.png)
![series](overlays/series_p01.png)

## Review flags

| severity | stage | panel | reason |
|---|---|---|---|
| warning | select | p01 | best candidate coverage 0.742 below viability gate 0.985 |
| warning | series | p01 | 8 empty slice(s): 1844-01-01, 1844-01-07, 1844-01-08, 1844-01-09, 1844-01-10... |
| info | qc |  | skipped: No GEMINI_API_KEY / GOOGLE_API_KEY found. Copy .env.example to .env and add your key, or export it in the environment. |
