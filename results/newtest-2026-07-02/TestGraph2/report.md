# Run report: 20260702-221205-TestGraph2

- profile: **generic**
- graphdig: 0.1.0
- input: `pages/TestGraph2.png` (752x394)

## Panels

| panel | label | bbox (x,y,w,h) | conf | flags |
|---|---|---|---|---|
| p01 | Fig. 83. | 32,59,652,272 | 0.80 |  |

![panels](overlays/panels.png)

## Calibration

| panel | unit | scale | slope (unit/px) | r2 | ticks used | flags |
|---|---|---|---|---|---|---|
| p01 | unknown | linear | - | - | - | unusable |

## Extraction (lineformer_local)

| panel | candidates | selected | conf | coverage | s_alpha | method |
|---|---|---|---|---|---|---|
| p01 | 93 | 0 | 0.871 | 0.920 | 0.905 | s_alpha |

## Series

## Review flags

| severity | stage | panel | reason |
|---|---|---|---|
| warning | triage |  | no axis labels and no curve labels: absolute calibration impossible from this image alone (relative digitization only) |
| blocking | calibrate | p01 | no usable axis fit (0 calibration points) |
| warning | select | p01 | best candidate coverage 0.920 below viability gate 0.985 |
| blocking | series | p01 | no usable axis calibration |
