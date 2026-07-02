# GraphDigitization

Automated digitization of historical line charts (hydrographs, forestry yield curves, …) by
combining a multimodal LLM with a transformer line-extraction model:

- **Gemini 3.5 Flash** does the *semantic* work that human annotators previously did by hand:
  chart panel detection, y-axis tick reading and calibration, metadata extraction, baseline
  (zero-line) localization, and visual quality control.
- **[LineFormer](https://github.com/TheJaeLal/LineFormer)** (ICDAR 2023) does the *pixel* work:
  polyline instance segmentation of the drawn curve.
- Plain Python does the *math*: least-squares axis fits with outlier rejection, warp correction,
  resampling, and evaluation metrics.

The pipeline automates the manual annotation steps of the HWLR workflow described in
Rehbein, *Reconstructing nineteenth-century Danube river water levels with transformer-based
computer vision* (Earth Syst. Sci. Data 18, 1783–1811, 2026), and generalizes it to arbitrary
historical line charts. Reference data: [Zenodo 17296751](https://zenodo.org/records/17296751)
(CC-BY-4.0).

> Status: under construction — see `docs/design.md` for the architecture.

## Quick start

```bash
uv sync                                     # main environment (Python 3.12)
cp .env.example .env                        # add your GEMINI_API_KEY
uv run graphdig run data/samples/forestry_A382_019.jpeg --profile generic
```

LineFormer runs in a separate pinned environment (old torch/mmdet stack):

```powershell
./scripts/setup_lineformer_env.ps1          # local CPU inference (py3.10 venv)
```

or on GPU via `notebooks/lineformer_colab.ipynb` (export a job bundle with
`graphdig export-job`, run it on Colab, then `graphdig import-results`).

## License

MIT for this repository. LineFormer is cloned as an external dependency (no license published);
its code is never vendored here. Zenodo dataset content is CC-BY-4.0 (Rehbein, 2025).
