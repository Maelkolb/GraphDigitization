# Whole-pipeline hardening — 2026-07-03

The round that makes the pipeline work "regardless of source graph": user-suppliable
metadata hints, FULL annual hydrograph sheets (segmentation included), and a second
extraction backend benchmarked head-to-head against LineFormer.
Full architecture: `docs/how_it_works.md`.

## What's new

1. **User hints** (`--hints hints.json`): station, year, unit, scale, rotation, series
   census, expected panels, per-panel months/extents/bboxes, manual y-anchors. Hints
   override Gemini; every disagreement is flagged (`hint_mismatch:*`), never silent.
2. **Full annual sheets**: 12-panel segmentation with calendar-order month assignment,
   over/under-segmentation repair at gridline seams, month-width day-shift guards,
   shared-scale donor calibration, page-margin label retries, and a stitched
   `series/annual.csv` + full-year figure per run.
3. **Pseudo-pages** (`graphdig pseudo-page <scan> <year> --run`): full-sheet stand-ins
   stitched from the dataset tiles with truth + hints sidecars;
   `graphdig evaluate fullpage` measures segmentation IoU, edge error in DAYS, and
   per-month series accuracy. Real sheets run the identical path.
4. **`gemini_points` extractor** + `--extractor-fallback`: Gemini traces each named
   series directly (visibility-honest gaps); QC merges fallback candidates once per tile
   when majors persist. `graphdig evaluate extractors` benchmarks backends.

## Live results

**Full annual sheets, digitized in ONE run each** (12/12 panels segmented, month
identities correct, per-month series vs pixel GT; `fullpage_eval.csv` has every month):

| pseudo-page | panels | mean IoU | median \|edge error\| | peak score mean / median |
|---|---|---|---|---|
| Neu-Ulm 1839 (210018) | 12/12 | 0.853 | 1.92 days | 0.871 / 0.861 |
| Vilshofen 1844 (290022) | 12/12 | 0.892 | **0.26 days** | **0.967 / 0.981** |
| Passau 1848 (300026) | 12/12 | 0.952 | 0.29 days | 0.891 / 0.925 |

Vilshofen's full-page run reaches the paper's human-assisted accuracy level (its
tile-by-tile pilot scored 0.96 on the same months). Reference: paper's human-picked mean
on the whole GT sample was 0.968.

**Extractor benchmark — LineFormer vs gemini_points, 12 GT months (Neu-Ulm 1839) with
identical seeded calibration** (`extractor_bench.csv`, `comparison_*.md`):

| backend | peak mean | peak median | min | wall/month |
|---|---|---|---|---|
| lineformer_local (CPU) | 0.965 | 0.973 | 0.912 | 11.6 s |
| gemini_points | 0.964 | **0.986** | 0.817 | 26.9 s |

A statistical tie — gemini_points wins 8 of 12 months. Practical consequence: **the
pipeline digitizes hydrograph-class charts at near-equal quality with no LineFormer
environment at all** (no pinned venv, no GPU, no Colab). LineFormer stays the default
for its consistency (higher minimum) and speed.

**Weak cases (dense log grids, faint dotted curves)**: gemini_points did NOT rescue
them — QC majors for both backends on TestGraph6 and forestry A381-II. Precise tracing
on dense/degraded multi-curve material remains the open bottleneck for BOTH approaches;
fine-tuning LineFormer on historical charts is the remaining lever. Every weak curve is
honestly QC-flagged, never silently wrong.

**Regression guard**: Danube Feb 1839 single-tile run = 0.9835, bit-identical through
all six phases. Offline suite: 112 tests; live smokes green.

## A bug the evaluation caught (worth reading)

The first pseudo-page run scored IoU 0.24 with months scrambled: panels in one visual
row have wildly different heights (each month's chart is only as tall as its water
levels), and the reading-order sort banded them into phantom rows — while Gemini had
actually read the month names correctly off the charts. The fix (vertical-overlap row
clustering checked against every row member) is regression-pinned with the real heights
from that failure. This is exactly what the truth-file evaluation exists for.
