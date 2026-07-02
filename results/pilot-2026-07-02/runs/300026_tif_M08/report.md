# Run report: 20260702-031157-300026_tif_M08

- profile: **danube**
- graphdig: 0.1.0
- input: `pages/300026_M08.png` (714x657)

## Panels

| panel | label | bbox (x,y,w,h) | conf | flags |
|---|---|---|---|---|
| p01 | M08 | 0,0,714,657 | 1.00 | seeded_from_annotations |

![panels](overlays/panels.png)

## Calibration

| panel | unit | scale | slope (unit/px) | r2 | ticks used | flags |
|---|---|---|---|---|---|---|
| p01 | bavarian_foot | linear | -0.010823 | 1.0000 | 2/2 | seeded_from_annotations |

## Extraction (lineformer_local)

| panel | candidates | selected | conf | coverage | s_alpha | method |
|---|---|---|---|---|---|---|
| p01 | 74 | 2 | 0.647 | 0.871 | 0.802 | s_alpha |

## Series

### p01
- csv: `series/p01.csv` (31 samples, 4 gaps, baseline off)
- confidence chain: panel=1.00, calibration=1.00, extraction=0.65, coverage=0.87

![curve](overlays/curve_p01.png)
![series](overlays/series_p01.png)

## Review flags

| severity | stage | panel | reason |
|---|---|---|---|
| warning | select | p01 | best candidate coverage 0.871 below viability gate 0.985 |
| warning | series | p01 | 4 empty slice(s): 1848-08-16, 1848-08-17, 1848-08-20, 1848-08-26 |
| info | qc |  | skipped: No GEMINI_API_KEY / GOOGLE_API_KEY found. Copy .env.example to .env and add your key, or export it in the environment. |
