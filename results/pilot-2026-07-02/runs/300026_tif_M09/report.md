# Run report: 20260702-031202-300026_tif_M09

- profile: **danube**
- graphdig: 0.1.0
- input: `pages/300026_M09.png` (693x532)

## Panels

| panel | label | bbox (x,y,w,h) | conf | flags |
|---|---|---|---|---|
| p01 | M09 | 0,0,693,532 | 1.00 | seeded_from_annotations |

![panels](overlays/panels.png)

## Calibration

| panel | unit | scale | slope (unit/px) | r2 | ticks used | flags |
|---|---|---|---|---|---|---|
| p01 | bavarian_foot | linear | -0.010823 | 1.0000 | 2/2 | seeded_from_annotations |

## Extraction (lineformer_local)

| panel | candidates | selected | conf | coverage | s_alpha | method |
|---|---|---|---|---|---|---|
| p01 | 100 | 0 | 0.774 | 1.000 | 0.930 | s_alpha |

## Series

### p01
- csv: `series/p01.csv` (30 samples, 0 gaps, baseline off)
- confidence chain: panel=1.00, calibration=1.00, extraction=0.77, coverage=1.00

![curve](overlays/curve_p01.png)
![series](overlays/series_p01.png)

## Review flags

| severity | stage | panel | reason |
|---|---|---|---|
| info | qc |  | skipped: No GEMINI_API_KEY / GOOGLE_API_KEY found. Copy .env.example to .env and add your key, or export it in the environment. |
