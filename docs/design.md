# Architecture

## What this automates

The HWLR pipeline (Rehbein 2026) digitizes hand-drawn hydrographs with LineFormer, but
keeps four human-labor steps that its own conclusion names as the bottlenecks. This project
replaces each with a Gemini 3.5 Flash call plus deterministic verification:

| manual step (paper) | human cost | automated by |
|---|---|---|
| month/panel bounding boxes (`month_annotator`) | ~160 s/gauge-year | `stages/triage.py` (one-shot classification + panels + metadata) + CV gridline edge snapping |
| y-axis anchor extraction (2 anchors) | included above | `stages/calibrate.py`: Gemini reads ALL legible ticks (or values written along the curve on axis-less charts), IRLS/MAD least-squares fit with R²/residual gates (self-verification the 2-anchor method cannot do) |
| zero-line polyline (`baseline_annotator.py`) | ~27 s/page | `stages/baseline.py`: Gemini seeds k points, CV snaps them sub-pixel to the dark ridge |
| candidate pick + inspection (`inspector.py`) | ~3 s/month | `stages/select.py` (paper's s_alpha Eq. 12) + `stages/qc.py` (Gemini judge; majors trigger automatic candidate reselection) |

Confidence-gated human fallback everywhere: anything below a gate lands in
`review/flags.json` instead of failing silently or being trusted blindly.

## Division of labor

- **Gemini** (semantic): panels, tick reading, metadata, baseline seeds, QC verdicts,
  near-tie candidate picks. Never does math; never does pixel-level segmentation
  (unsupported in Gemini 3.x anyway).
- **LineFormer** (pixel): polyline instance segmentation of the drawn curve, in an
  isolated pinned environment (old torch/mmdet stack).
- **Plain Python** (math): least-squares axis fits with outlier rejection, warp
  correction (paper Eqs. 9-11), last-per-slice resampling, unit conversion, metrics.

## Artifact-based staged pipeline

```
ingest -> triage -> calibrate -> [baseline] -> preprocess
       -> extract -> select -> series -> qc (auto-reselect loop) -> report
```

Full walk-through: `docs/how_it_works.md`.

Each stage reads/writes JSON+PNG artifacts in a run directory (`outputs/runs/<run_id>/`):
`manifest.json` (config, stage status), `panels.json`, `calibration.json`,
`metadata.json`, `baseline.json`, `tiles.json` (with `Transform2D` tile<->page),
`lines.json` (candidates + selection), `series/<panel>.csv`, `qc.json`,
`review/flags.json`, `report.md`, `overlays/*.png`.

Consequences:
- any stage can be re-run (`--stages`, `--force`), inspected, or diffed;
- the pixel-heavy extract stage is **detachable**: `export-job` zips tiles + job spec +
  worker script; Colab (or any GPU box) runs `lineformer_infer.py`; `import-results`
  merges and the run resumes locally (see docs/colab.md);
- every Gemini output carries `provenance` (model, prompt id, thinking level, usage).

## Profiles

`danube` (12 monthly panels, daily sampling, Bavarian-foot/mm transition 1872-04-01,
baseline correction on, gridline x-edge refinement on) vs `generic` (N panels, x-axis
calibration decides sampling). Prompt variants live in `gemini/prompts.py`, versioned —
never edit a prompt in place.

## Paper constants baked in (all configurable)

x-stretch s=2.0 (bicubic, x only) · last-point-per-slice resampling ·
s_alpha = 0.31·confidence + 0.69·coverage · coverage viable > 0.985 ·
peak-aware composite 0.4·r + 0.4·s_peakval + 0.2·s_peaktime ·
Bavarian foot = 291.859 mm.

## Environments

- main env: `uv sync` (Python 3.12, google-genai v2, no torch);
- `.venvs/lineformer`: `scripts/setup_lineformer_env.ps1|.sh` (Python 3.10,
  torch 1.13.1 CPU, mmcv-full 1.7.x, mmdet 2.28.2, LineFormer clone under gitignored
  `external/` — the repo publishes no license, so its code is never vendored);
- Colab GPU: `notebooks/lineformer_colab.ipynb` (T4/cu117).

Local GPU note: Blackwell cards (RTX 50xx) cannot run cu117 binaries; that is why local
inference is CPU-only and the GPU path goes through Colab.

## Testing

`uv run pytest` — offline suite (unit math incl. exact paper-equation tests; full
pipeline against a synthetic chart with analytic ground truth, canned Gemini responses,
stub extractor; ranged-zip against an in-process Range-honoring HTTP server; bundle
round-trip). Markers: `-m live` (needs `GEMINI_API_KEY`), `-m lineformer` (needs the
pinned venv); both excluded by default.
