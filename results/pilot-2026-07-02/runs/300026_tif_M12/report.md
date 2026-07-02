# Run report: 20260702-031217-300026_tif_M12

- profile: **danube**
- graphdig: 0.1.0
- input: `pages/300026_M12.png` (718x615)

## Panels

| panel | label | bbox (x,y,w,h) | conf | flags |
|---|---|---|---|---|
| p01 | M12 | 0,0,718,615 | 1.00 | seeded_from_annotations |

![panels](overlays/panels.png)

## Calibration

| panel | unit | scale | slope (unit/px) | r2 | ticks used | flags |
|---|---|---|---|---|---|---|
| p01 | bavarian_foot | linear | -0.010823 | 1.0000 | 2/2 | seeded_from_annotations |

## Extraction (lineformer_local)

| panel | candidates | selected | conf | coverage | s_alpha | method |
|---|---|---|---|---|---|---|
| p01 | 94 | 0 | 0.842 | 0.935 | 0.906 | s_alpha |

## Series

### p01
- csv: `series/p01.csv` (31 samples, 2 gaps, baseline off)
- confidence chain: panel=1.00, calibration=1.00, extraction=0.84, coverage=0.94

![curve](overlays/curve_p01.png)
![series](overlays/series_p01.png)

## Review flags

| severity | stage | panel | reason |
|---|---|---|---|
| warning | select | p01 | best candidate coverage 0.935 below viability gate 0.985 |
| warning | series | p01 | 2 empty slice(s): 1848-12-30, 1848-12-31 |
| info | qc |  | skipped: No GEMINI_API_KEY / GOOGLE_API_KEY found. Copy .env.example to .env and add your key, or export it in the environment. |
