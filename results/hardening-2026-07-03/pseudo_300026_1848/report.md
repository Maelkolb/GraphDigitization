# Run report: 20260703-012123-pseudo_300026_1848

- profile: **danube**
- graphdig: 0.1.0
- input: `pages/pseudo_300026_1848.png` (8388x1924)

## Panels

| panel | label | bbox (x,y,w,h) | conf | flags |
|---|---|---|---|---|
| p01 | Januar | 0,1449,721,463 | 0.95 |  |
| p02 | Februar | 721,0,638,1912 | 0.95 | month_width_outlier |
| p03 | März | 1359,1301,721,611 | 0.95 |  |
| p04 | April | 2080,1505,688,407 | 0.95 |  |
| p05 | Mai | 2768,1532,696,380 | 0.95 | month_width_outlier |
| p06 | Juni | 3464,1380,655,532 | 0.95 | month_width_outlier |
| p07 | Juli | 4119,1095,721,817 | 0.95 |  |
| p08 | August | 4840,1260,704,652 | 0.95 | month_width_outlier |
| p09 | September | 5544,1380,697,532 | 0.95 |  |
| p10 | Oktober | 6241,1347,729,565 | 0.95 |  |
| p11 | November | 6970,1505,697,407 | 0.95 |  |
| p12 | Dezember | 7667,1306,721,606 | 0.95 |  |

![panels](overlays/panels.png)

## Calibration

| panel | unit | scale | slope (unit/px) | r2 | ticks used | flags |
|---|---|---|---|---|---|---|
| p01 | bavarian_foot | linear | -0.010823 | 1.0000 | 2/2 | user_hint:y_anchors, two_anchor_only |
| p02 | bavarian_foot | linear | -0.010823 | 1.0000 | 2/2 | user_hint:y_anchors, two_anchor_only |
| p03 | bavarian_foot | linear | -0.010823 | 1.0000 | 2/2 | user_hint:y_anchors, two_anchor_only |
| p04 | bavarian_foot | linear | -0.010823 | 1.0000 | 2/2 | user_hint:y_anchors, two_anchor_only |
| p05 | bavarian_foot | linear | -0.010823 | 1.0000 | 2/2 | user_hint:y_anchors, two_anchor_only |
| p06 | bavarian_foot | linear | -0.010823 | 1.0000 | 2/2 | user_hint:y_anchors, two_anchor_only |
| p07 | bavarian_foot | linear | -0.010823 | 1.0000 | 2/2 | user_hint:y_anchors, two_anchor_only |
| p08 | bavarian_foot | linear | -0.010823 | 1.0000 | 2/2 | user_hint:y_anchors, two_anchor_only |
| p09 | bavarian_foot | linear | -0.010823 | 1.0000 | 2/2 | user_hint:y_anchors, two_anchor_only |
| p10 | bavarian_foot | linear | -0.010823 | 1.0000 | 2/2 | user_hint:y_anchors, two_anchor_only |
| p11 | bavarian_foot | linear | -0.010823 | 1.0000 | 2/2 | user_hint:y_anchors, two_anchor_only |
| p12 | bavarian_foot | linear | -0.010823 | 1.0000 | 2/2 | user_hint:y_anchors, two_anchor_only |

## Extraction (lineformer_local)

| panel | candidates | selected | conf | coverage | s_alpha | method |
|---|---|---|---|---|---|---|
| p01 | 100 | 14 | 0.054 | 1.000 | 0.707 | gemini_pick |
| p02 | 100 | 6 | 0.040 | 1.000 | 0.703 | gemini_pick |
| p03 | 99 | 1 | 0.796 | 0.968 | 0.914 | s_alpha |
| p04 | 100 | 4 | 0.710 | 0.833 | 0.795 | qc_reselect_s_alpha |
| p05 | 99 | 16 | 0.016 | 1.000 | 0.695 | gemini_pick |
| p06 | 95 | 2 | 0.800 | 0.767 | 0.777 | qc_reselect_s_alpha |
| p07 | 100 | 2 | 0.719 | 0.774 | 0.757 | qc_reselect_s_alpha |
| p08 | 95 | 2 | 0.732 | 0.871 | 0.828 | qc_reselect_s_alpha |
| p09 | 100 | 3 | 0.733 | 0.967 | 0.894 | s_alpha |
| p10 | 99 | 89 | 0.002 | 1.000 | 0.691 | qc_reselect_s_alpha |
| p11 | 83 | 24 | 0.009 | 1.000 | 0.693 | qc_reselect_s_alpha |
| p12 | 90 | 3 | 0.746 | 0.871 | 0.832 | qc_reselect_s_alpha |

## Series

### Annual series (stitched from all monthly panels)
- csv: `series/annual.csv` (366 days, 27 gaps)

![annual](overlays/reconstruction_annual.png)

### p01
- csv: `series/p01.csv` (31 samples, 0 gaps, baseline off)
  - confidence chain: panel=0.95, calibration=1.00, extraction=0.05, coverage=1.00
  - QC: **ok** The red curve follows the hand-drawn curve very accurately across the entire length of the tile.

![series](overlays/reconstruction_p01.png)

### p02
- csv: `series/p02.csv` (29 samples, 0 gaps, baseline off)
  - confidence chain: panel=0.95, calibration=1.00, extraction=0.04, coverage=1.00
  - QC: **minor** The red curve slightly flattens and misses the peak of the smaller secondary crest on the right.

![series](overlays/reconstruction_p02.png)

### p03
- csv: `series/p03.csv` (31 samples, 1 gaps, baseline off)
  - confidence chain: panel=0.95, calibration=1.00, extraction=0.80, coverage=0.97
  - QC: **minor** The extracted curve slightly rounds out the sharp valley and peak points instead of following their exact tips.

![series](overlays/reconstruction_p03.png)

### p04
- csv: `series/p04.csv` (30 samples, 5 gaps, baseline off)
  - confidence chain: panel=0.95, calibration=1.00, extraction=0.71, coverage=0.83
  - QC: **major** The red curve cuts straight through the second peak and fails to track the rising curve at the right end.

![series](overlays/reconstruction_p04.png)

### p05
- csv: `series/p05.csv` (31 samples, 0 gaps, baseline off)
  - confidence chain: panel=0.95, calibration=1.00, extraction=0.02, coverage=1.00
  - QC: **ok** The extracted curve follows the hand-drawn line very closely within one grid unit throughout the entire segment.

![series](overlays/reconstruction_p05.png)

### p06
- csv: `series/p06.csv` (30 samples, 7 gaps, baseline off)
  - confidence chain: panel=0.95, calibration=1.00, extraction=0.80, coverage=0.77
  - QC: **major** The red curve fails to capture the main high peak and the third broad peak, cutting straight through them.

![series](overlays/reconstruction_p06.png)

### p07
- csv: `series/p07.csv` (31 samples, 7 gaps, baseline off)
  - confidence chain: panel=0.95, calibration=1.00, extraction=0.72, coverage=0.77
  - QC: **major** The red curve shortcuts through the central rising edge, misses the high peak on the second plateau, and fails to trace the oscillations on the right.

![series](overlays/reconstruction_p07.png)

### p08
- csv: `series/p08.csv` (31 samples, 4 gaps, baseline off)
  - confidence chain: panel=0.95, calibration=1.00, extraction=0.73, coverage=0.87
  - QC: **major** The red curve completely misses the large peak in the right-middle section, cutting straight across instead of following the curve.

![series](overlays/reconstruction_p08.png)

### p09
- csv: `series/p09.csv` (30 samples, 1 gaps, baseline off)
  - confidence chain: panel=0.95, calibration=1.00, extraction=0.73, coverage=0.97
  - QC: **ok** The red curve accurately traces the center of the drawn line across the entire tile.

![series](overlays/reconstruction_p09.png)

### p10
- csv: `series/p10.csv` (31 samples, 0 gaps, baseline off)
  - confidence chain: panel=0.95, calibration=1.00, extraction=0.00, coverage=1.00
  - QC: **major** The red curve completely misses all major peaks, tracing a flat baseline instead.

![series](overlays/reconstruction_p10.png)

### p11
- csv: `series/p11.csv` (30 samples, 0 gaps, baseline off)
  - confidence chain: panel=0.95, calibration=1.00, extraction=0.01, coverage=1.00
  - QC: **minor** The red curve flatlines below the plateau in the first half and has noisy spikes around the sharp peak.

![series](overlays/reconstruction_p11.png)

### p12
- csv: `series/p12.csv` (31 samples, 4 gaps, baseline off)
  - confidence chain: panel=0.95, calibration=1.00, extraction=0.75, coverage=0.87
  - QC: **major** The extracted curve completely misses the hand-drawn line on the left half, tracing a flat horizontal path instead.

![series](overlays/reconstruction_p12.png)

## Review flags

| severity | stage | panel | reason |
|---|---|---|---|
| warning | triage |  | no axis labels and no curve labels: absolute calibration impossible from this image alone (relative digitization only) |
| warning | triage | p02 | panel width implies 27.5 days, month has 29 (possible edge error) |
| warning | triage | p05 | panel width implies 30.0 days, month has 31 (possible edge error) |
| warning | triage | p06 | panel width implies 28.2 days, month has 30 (possible edge error) |
| warning | triage | p08 | panel width implies 30.3 days, month has 31 (possible edge error) |
| warning | calibrate | p04 | only 2 calibration points; using two-anchor mapping |
| warning | calibrate | p01 | only 2 calibration points; using two-anchor mapping |
| warning | calibrate | p03 | only 2 calibration points; using two-anchor mapping |
| warning | calibrate | p05 | only 2 calibration points; using two-anchor mapping |
| warning | calibrate | p02 | only 2 calibration points; using two-anchor mapping |
| warning | calibrate | p06 | only 2 calibration points; using two-anchor mapping |
| warning | calibrate | p07 | only 2 calibration points; using two-anchor mapping |
| warning | calibrate | p08 | only 2 calibration points; using two-anchor mapping |
| warning | calibrate | p09 | only 2 calibration points; using two-anchor mapping |
| warning | calibrate | p11 | only 2 calibration points; using two-anchor mapping |
| warning | calibrate | p10 | only 2 calibration points; using two-anchor mapping |
| warning | calibrate | p12 | only 2 calibration points; using two-anchor mapping |
| warning | select | p03 | best candidate coverage 0.968 below viability gate 0.985 |
| warning | select | p04 | best candidate coverage 0.800 below viability gate 0.985 |
| warning | select | p06 | best candidate coverage 0.933 below viability gate 0.985 |
| warning | select | p07 | best candidate coverage 0.774 below viability gate 0.985 |
| warning | select | p08 | best candidate coverage 0.903 below viability gate 0.985 |
| warning | select | p09 | best candidate coverage 0.967 below viability gate 0.985 |
| warning | select | p10 | best candidate coverage 0.839 below viability gate 0.985 |
| warning | select | p12 | best candidate coverage 0.935 below viability gate 0.985 |
| warning | series | p03 | 1 empty slice(s): 1848-03-31 |
| warning | series | p04 | 6 empty slice(s): 1848-04-01, 1848-04-02, 1848-04-03, 1848-04-15, 1848-04-29... |
| warning | series | p06 | 2 empty slice(s): 1848-06-10, 1848-06-11 |
| warning | series | p07 | 7 empty slice(s): 1848-07-01, 1848-07-02, 1848-07-03, 1848-07-04, 1848-07-05... |
| warning | series | p08 | 3 empty slice(s): 1848-08-20, 1848-08-21, 1848-08-26 |
| warning | series | p09 | 1 empty slice(s): 1848-09-27 |
| warning | series | p10 | 5 empty slice(s): 1848-10-01, 1848-10-02, 1848-10-12, 1848-10-17, 1848-10-31 |
| warning | series | p12 | 2 empty slice(s): 1848-12-30, 1848-12-31 |
| warning | qc | p02 | minor deviation: The red curve slightly flattens and misses the peak of the smaller secondary crest on the right. |
| warning | qc | p03 | minor deviation: The extracted curve slightly rounds out the sharp valley and peak points instead of following their exact tips. |
| info | qc | p04 | QC rejected candidate; reselected cand 4 |
| warning | series | p04 | 5 empty slice(s): 1848-04-01, 1848-04-02, 1848-04-03, 1848-04-08, 1848-04-09 |
| blocking | qc | p04 | major deviation persists: The red curve cuts straight through the second peak and fails to track the rising curve at the right end. |
| info | qc | p06 | QC rejected candidate; reselected cand 2 |
| warning | series | p06 | 7 empty slice(s): 1848-06-01, 1848-06-07, 1848-06-09, 1848-06-10, 1848-06-11... |
| blocking | qc | p06 | major deviation persists: The red curve fails to capture the main high peak and the third broad peak, cutting straight through them. |
| info | qc | p07 | QC rejected candidate; reselected cand 2 |
| warning | series | p07 | 7 empty slice(s): 1848-07-01, 1848-07-02, 1848-07-10, 1848-07-11, 1848-07-12... |
| blocking | qc | p07 | major deviation persists: The red curve shortcuts through the central rising edge, misses the high peak on the second plateau, and fails to trace the oscillations on the right. |
| info | qc | p08 | QC rejected candidate; reselected cand 2 |
| warning | series | p08 | 4 empty slice(s): 1848-08-20, 1848-08-21, 1848-08-26, 1848-08-27 |
| blocking | qc | p08 | major deviation persists: The red curve completely misses the large peak in the right-middle section, cutting straight across instead of following the curve. |
| info | qc | p10 | QC rejected candidate; reselected cand 89 |
| blocking | qc | p10 | major deviation persists: The red curve completely misses all major peaks, tracing a flat baseline instead. |
| info | qc | p11 | QC rejected candidate; reselected cand 24 |
| warning | qc | p11 | minor deviation: The red curve flatlines below the plateau in the first half and has noisy spikes around the sharp peak. |
| info | qc | p12 | QC rejected candidate; reselected cand 3 |
| warning | series | p12 | 4 empty slice(s): 1848-12-01, 1848-12-07, 1848-12-30, 1848-12-31 |
| blocking | qc | p12 | major deviation persists: The extracted curve completely misses the hand-drawn line on the left half, tracing a flat horizontal path instead. |
