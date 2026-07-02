# Run report: 20260703-011645-pseudo_210018_1839

- profile: **danube**
- graphdig: 0.1.0
- input: `pages/pseudo_210018_1839.png` (8399x947)

## Panels

| panel | label | bbox (x,y,w,h) | conf | flags |
|---|---|---|---|---|
| p01 |  | 0,492,697,455 | 0.95 | month_width_outlier |
| p02 |  | 697,0,647,947 | 0.95 |  |
| p03 |  | 1344,369,739,578 | 0.95 | month_width_outlier |
| p04 |  | 2083,563,638,384 | 0.95 | month_width_outlier |
| p05 |  | 2721,597,723,350 | 0.95 |  |
| p06 |  | 3444,464,730,483 | 0.95 | month_width_outlier |
| p07 |  | 4174,625,731,322 | 0.95 |  |
| p08 |  | 4905,587,722,360 | 0.95 |  |
| p09 |  | 5627,419,714,528 | 0.95 | month_width_outlier |
| p10 |  | 6341,597,731,350 | 0.95 |  |
| p11 |  | 7072,724,663,223 | 0.95 | month_width_outlier |
| p12 |  | 7735,185,664,762 | 0.95 | month_width_outlier |

![panels](overlays/panels.png)

## Calibration

| panel | unit | scale | slope (unit/px) | r2 | ticks used | flags |
|---|---|---|---|---|---|---|
| p01 | bavarian_foot | linear | -0.010548 | 1.0000 | 2/2 | user_hint:y_anchors, two_anchor_only |
| p02 | bavarian_foot | linear | -0.010548 | 1.0000 | 2/2 | user_hint:y_anchors, two_anchor_only |
| p03 | bavarian_foot | linear | -0.010548 | 1.0000 | 2/2 | user_hint:y_anchors, two_anchor_only |
| p04 | bavarian_foot | linear | -0.010548 | 1.0000 | 2/2 | user_hint:y_anchors, two_anchor_only |
| p05 | bavarian_foot | linear | -0.010548 | 1.0000 | 2/2 | user_hint:y_anchors, two_anchor_only |
| p06 | bavarian_foot | linear | -0.010548 | 1.0000 | 2/2 | user_hint:y_anchors, two_anchor_only |
| p07 | bavarian_foot | linear | -0.010548 | 1.0000 | 2/2 | user_hint:y_anchors, two_anchor_only |
| p08 | bavarian_foot | linear | -0.010548 | 1.0000 | 2/2 | user_hint:y_anchors, two_anchor_only |
| p09 | bavarian_foot | linear | -0.010548 | 1.0000 | 2/2 | user_hint:y_anchors, two_anchor_only |
| p10 | bavarian_foot | linear | -0.010548 | 1.0000 | 2/2 | user_hint:y_anchors, two_anchor_only |
| p11 | bavarian_foot | linear | -0.010548 | 1.0000 | 2/2 | user_hint:y_anchors, two_anchor_only |
| p12 | bavarian_foot | linear | -0.010548 | 1.0000 | 2/2 | user_hint:y_anchors, two_anchor_only |

## Extraction (lineformer_local)

| panel | candidates | selected | conf | coverage | s_alpha | method |
|---|---|---|---|---|---|---|
| p01 | 99 | 0 | 0.923 | 1.000 | 0.976 | s_alpha |
| p02 | 100 | 1 | 0.873 | 1.000 | 0.961 | s_alpha |
| p03 | 100 | 0 | 0.899 | 1.000 | 0.969 | s_alpha |
| p04 | 85 | 0 | 0.925 | 1.000 | 0.977 | s_alpha |
| p05 | 98 | 6 | 0.031 | 1.000 | 0.700 | qc_reselect_s_alpha |
| p06 | 99 | 0 | 0.886 | 1.000 | 0.965 | s_alpha |
| p07 | 100 | 0 | 0.934 | 1.000 | 0.980 | s_alpha |
| p08 | 100 | 0 | 0.896 | 1.000 | 0.968 | s_alpha |
| p09 | 99 | 0 | 0.882 | 1.000 | 0.963 | s_alpha |
| p10 | 99 | 0 | 0.940 | 1.000 | 0.981 | s_alpha |
| p11 | 99 | 0 | 0.940 | 1.000 | 0.981 | s_alpha |
| p12 | 99 | 0 | 0.905 | 1.000 | 0.970 | s_alpha |

## Series

### Annual series (stitched from all monthly panels)
- csv: `series/annual.csv` (365 days, 0 gaps)

![annual](overlays/reconstruction_annual.png)

### p01
- csv: `series/p01.csv` (31 samples, 0 gaps, baseline off)
  - confidence chain: panel=0.95, calibration=1.00, extraction=0.92, coverage=1.00
  - QC: **ok** The extracted curve follows the hand-drawn line very closely across the entire length, with only negligible rounding at the sharpest peaks.

![series](overlays/reconstruction_p01.png)

### p02
- csv: `series/p02.csv` (28 samples, 0 gaps, baseline off)
  - confidence chain: panel=0.95, calibration=1.00, extraction=0.87, coverage=1.00
  - QC: **ok** The red curve accurately tracks the hand-drawn curve across the entire image within one grid tick.

![series](overlays/reconstruction_p02.png)

### p03
- csv: `series/p03.csv` (31 samples, 0 gaps, baseline off)
  - confidence chain: panel=0.95, calibration=1.00, extraction=0.90, coverage=1.00
  - QC: **minor** The red curve has a slight vertical offset along the main decline and connects a gap between the two disjoint line segments at the start.

![series](overlays/reconstruction_p03.png)

### p04
- csv: `series/p04.csv` (30 samples, 0 gaps, baseline off)
  - confidence chain: panel=0.95, calibration=1.00, extraction=0.93, coverage=1.00
  - QC: **ok** The extracted curve follows the original hand-drawn line extremely closely across the entire length of the segment.

![series](overlays/reconstruction_p04.png)

### p05
- csv: `series/p05.csv` (31 samples, 0 gaps, baseline off)
  - confidence chain: panel=0.95, calibration=1.00, extraction=0.03, coverage=1.00
  - QC: **minor** The red curve fails to capture the full height of the sharp peak on the right side of the chart.

![series](overlays/reconstruction_p05.png)

### p06
- csv: `series/p06.csv` (30 samples, 0 gaps, baseline off)
  - confidence chain: panel=0.95, calibration=1.00, extraction=0.89, coverage=1.00
  - QC: **minor** The red curve generally follows the trend but exhibits minor vertical offsets and slightly rounds out some sharp peaks and valleys.

![series](overlays/reconstruction_p06.png)

### p07
- csv: `series/p07.csv` (31 samples, 0 gaps, baseline off)
  - confidence chain: panel=0.95, calibration=1.00, extraction=0.93, coverage=1.00
  - QC: **ok** The red curve accurately follows the main hand-drawn curve across the entire chart, correctly ignoring the faint erased peak.

![series](overlays/reconstruction_p07.png)

### p08
- csv: `series/p08.csv` (31 samples, 0 gaps, baseline off)
  - confidence chain: panel=0.95, calibration=1.00, extraction=0.90, coverage=1.00
  - QC: **minor** The extracted curve is slightly shifted vertically above the original line in the first half of the chart.

![series](overlays/reconstruction_p08.png)

### p09
- csv: `series/p09.csv` (30 samples, 0 gaps, baseline off)
  - confidence chain: panel=0.95, calibration=1.00, extraction=0.88, coverage=1.00
  - QC: **ok** The extracted curve follows the original hand-drawn line extremely closely across the entire tile.

![series](overlays/reconstruction_p09.png)

### p10
- csv: `series/p10.csv` (31 samples, 0 gaps, baseline off)
  - confidence chain: panel=0.95, calibration=1.00, extraction=0.94, coverage=1.00
  - QC: **ok** The red curve closely follows the hand-drawn data curve within one grid tick across the entire segment.

![series](overlays/reconstruction_p10.png)

### p11
- csv: `series/p11.csv` (30 samples, 0 gaps, baseline off)
  - confidence chain: panel=0.95, calibration=1.00, extraction=0.94, coverage=1.00
  - QC: **minor** The red overlay deviates slightly from the data line at the far right section where it fails to track the downward step.

![series](overlays/reconstruction_p11.png)

### p12
- csv: `series/p12.csv` (31 samples, 0 gaps, baseline off)
  - confidence chain: panel=0.95, calibration=1.00, extraction=0.90, coverage=1.00
  - QC: **ok** The red curve follows the hand-drawn data curve extremely well across the entire image.

![series](overlays/reconstruction_p12.png)

## Review flags

| severity | stage | panel | reason |
|---|---|---|---|
| warning | triage |  | no axis labels and no curve labels: absolute calibration impossible from this image alone (relative digitization only) |
| warning | triage | p01 | panel width implies 29.9 days, month has 31 (possible edge error) |
| warning | triage | p03 | panel width implies 31.7 days, month has 31 (possible edge error) |
| warning | triage | p04 | panel width implies 27.4 days, month has 30 (possible edge error) |
| warning | triage | p06 | panel width implies 31.3 days, month has 30 (possible edge error) |
| warning | triage | p09 | panel width implies 30.6 days, month has 30 (possible edge error) |
| warning | triage | p11 | panel width implies 28.4 days, month has 30 (possible edge error) |
| warning | triage | p12 | panel width implies 28.5 days, month has 31 (possible edge error) |
| warning | calibrate | p04 | only 2 calibration points; using two-anchor mapping |
| warning | calibrate | p01 | only 2 calibration points; using two-anchor mapping |
| warning | calibrate | p03 | only 2 calibration points; using two-anchor mapping |
| warning | calibrate | p02 | only 2 calibration points; using two-anchor mapping |
| warning | calibrate | p05 | only 2 calibration points; using two-anchor mapping |
| warning | calibrate | p06 | only 2 calibration points; using two-anchor mapping |
| warning | calibrate | p07 | only 2 calibration points; using two-anchor mapping |
| warning | calibrate | p08 | only 2 calibration points; using two-anchor mapping |
| warning | calibrate | p09 | only 2 calibration points; using two-anchor mapping |
| warning | calibrate | p11 | only 2 calibration points; using two-anchor mapping |
| warning | calibrate | p10 | only 2 calibration points; using two-anchor mapping |
| warning | calibrate | p12 | only 2 calibration points; using two-anchor mapping |
| warning | qc | p03 | minor deviation: The red curve has a slight vertical offset along the main decline and connects a gap between the two disjoint line segments at the start. |
| info | qc | p05 | QC rejected candidate; reselected cand 6 |
| warning | qc | p05 | minor deviation: The red curve fails to capture the full height of the sharp peak on the right side of the chart. |
| warning | qc | p06 | minor deviation: The red curve generally follows the trend but exhibits minor vertical offsets and slightly rounds out some sharp peaks and valleys. |
| warning | qc | p08 | minor deviation: The extracted curve is slightly shifted vertically above the original line in the first half of the chart. |
| warning | qc | p11 | minor deviation: The red overlay deviates slightly from the data line at the far right section where it fails to track the downward step. |
