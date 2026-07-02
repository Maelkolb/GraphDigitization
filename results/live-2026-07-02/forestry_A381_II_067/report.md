# Run report: 20260702-111451-forestry_A381_II_067

- profile: **generic**
- graphdig: 0.1.0
- input: `pages/forestry_A381_II_067.png` (1652x1362)

## Panels

| panel | label | bbox (x,y,w,h) | conf | flags |
|---|---|---|---|---|
| p01 | Fichten
zur Probeflaeche N. 1.
/200. jährig/ | 66,123,1346,615 | 1.00 |  |
| p02 | Fichten
zur Probeflaeche N. 14.
/115 jährig/
Klingenbrunn | 91,729,1343,599 | 1.00 |  |

![panels](overlays/panels.png)

## Calibration

| panel | unit | scale | slope (unit/px) | r2 | ticks used | flags |
|---|---|---|---|---|---|---|
| p01 | unknown | linear | - | - | - | unusable |
| p02 | unknown | linear | - | - | - | unusable |

## Extraction (lineformer_local)

| panel | candidates | selected | conf | coverage | s_alpha | method |
|---|---|---|---|---|---|---|
| p01 | 93 | 2 | 0.112 | 0.990 | 0.718 | gemini_pick |
| p02 | 88 | 16 | 0.015 | 0.690 | 0.481 | s_alpha |

## Series

## Review flags

| severity | stage | panel | reason |
|---|---|---|---|
| blocking | calibrate | p01 | no usable axis fit (0 ticks) |
| blocking | calibrate | p02 | no usable axis fit (0 ticks) |
| warning | select | p02 | best candidate coverage 0.690 below viability gate 0.985 |
| blocking | series | p01 | no usable axis calibration |
| blocking | series | p02 | no usable axis calibration |
