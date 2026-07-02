# Sets up the pinned LineFormer environment (local CPU inference).
#
# LineFormer needs Python <=3.10, torch 1.13.1, mmcv-full 1.x, mmdet 2.x - an old stack
# that must stay isolated from the main graphdig env. GPU note: Blackwell-generation cards
# (e.g. RTX 5060) cannot run cu117 binaries; local inference is CPU-only by design, use
# notebooks/lineformer_colab.ipynb for GPU batch runs.
#
# Prerequisite: uv (https://docs.astral.sh/uv/):  irm https://astral.sh/uv/install.ps1 | iex

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "== creating .venvs/lineformer (Python 3.10) =="
uv venv .venvs/lineformer --python 3.10
$py = Join-Path $root ".venvs/lineformer/Scripts/python.exe"

Write-Host "== installing pinned torch 1.13.1 (CPU) =="
& $py -m pip install --quiet torch==1.13.1+cpu torchvision==0.14.1+cpu `
    --extra-index-url https://download.pytorch.org/whl/cpu
if ($LASTEXITCODE -ne 0) { throw "torch install failed" }

Write-Host "== installing mmcv-full 1.7.x + mmdet 2.28.2 (this can take a while) =="
& $py -m pip install --quiet -U openmim
& $py -m mim install "mmcv-full==1.7.1"
if ($LASTEXITCODE -ne 0) {
    Write-Warning "mmcv-full 1.7.1 wheel unavailable; trying 1.7.0"
    & $py -m mim install "mmcv-full==1.7.0"
    if ($LASTEXITCODE -ne 0) {
        throw ("mmcv-full install failed. Fallbacks: try mmcv-full 1.6.2, use WSL, or use " +
               "the Colab notebook (notebooks/lineformer_colab.ipynb) as the extraction backend.")
    }
}
& $py -m pip install --quiet "mmdet==2.28.2" "yapf==0.40.1" gdown opencv-python-headless "numpy<1.24"
if ($LASTEXITCODE -ne 0) { throw "mmdet install failed" }

Write-Host "== cloning LineFormer (external/, gitignored - no license published, never vendor) =="
if (-not (Test-Path "external/LineFormer")) {
    git clone --depth 1 https://github.com/TheJaeLal/LineFormer external/LineFormer
}

Write-Host "== checkpoint =="
$ckpt = Get-ChildItem "external/LineFormer" -Recurse -Filter "*.pth" -ErrorAction SilentlyContinue | Select-Object -First 1
if ($null -eq $ckpt) {
    Write-Host "No checkpoint found. Download iter_3000.pth via the Google Drive link in"
    Write-Host "external/LineFormer/README.md and place it in external/LineFormer/, e.g.:"
    Write-Host "  & $py -m gdown <GDRIVE_FILE_ID> -O external/LineFormer/iter_3000.pth"
} else {
    Write-Host "found checkpoint: $($ckpt.FullName)"
    Write-Host "== self-test =="
    & $py scripts/lineformer_infer.py --self-test
}
Write-Host "done."
