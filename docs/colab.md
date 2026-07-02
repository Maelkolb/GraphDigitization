# Running the extract stage on Colab (GPU)

LineFormer's pinned stack (torch 1.13.1 / CUDA 11.7 / mmdet 2.x) cannot use
Blackwell-generation local GPUs; Colab's T4 (sm_75) is compatible. The pipeline is built
around detachable job bundles so only the pixel-heavy extract stage moves to Colab.

## Round trip

```bash
# 1. local: run the semantic stages, stop at extract, export the bundle
uv run graphdig run page.jpeg --profile danube --extractor colab_bundle
#    (or, for an existing run: uv run graphdig export-job outputs/runs/<run_id>)
#    -> outputs/runs/<run_id>/colab/job_bundle_<run_id>.zip

# 2. Colab: open notebooks/lineformer_colab.ipynb (GPU runtime),
#    upload the bundle, Run All, download results_<run_id>.zip

# 3. local: merge results and finish the run
uv run graphdig import-results outputs/runs/<run_id> results_<run_id>.zip
uv run graphdig run --run-dir outputs/runs/<run_id> --stages select,series,qc,report
```

## Bundle contents

`job.json` (run id, params, tile list with sha256), `tiles/*.png` (preprocessed:
plot-area crop + x-stretch already applied), `lineformer_infer.py` (the standalone worker
— identical to the one the local CPU backend runs). Results: `results.json` with
per-tile candidates `{cand_id, confidence, points[[x,y],...]}` in tile coordinates.
`import-results` refuses bundles whose `run_id` does not match the run directory.

## Checkpoint

`iter_3000.pth` is distributed via the Google Drive link in the
[LineFormer README](https://github.com/TheJaeLal/LineFormer); paste its Drive file id
into the notebook (`CKPT_GDRIVE_ID`) or upload the file manually. Local setup
(`scripts/setup_lineformer_env.ps1`) expects it under `external/LineFormer/`.
