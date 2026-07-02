#!/usr/bin/env bash
# Pinned LineFormer environment (POSIX/WSL/Colab variant of setup_lineformer_env.ps1).
# For GPU (e.g. Colab T4): DEVICE=cu117 ./scripts/setup_lineformer_env.sh
set -euo pipefail
cd "$(dirname "$0")/.."

DEVICE="${DEVICE:-cpu}"   # cpu | cu117

echo "== creating .venvs/lineformer (Python 3.10) =="
uv venv .venvs/lineformer --python 3.10 --seed --clear
PY=".venvs/lineformer/bin/python"

echo "== installing pinned torch 1.13.1 ($DEVICE) =="
"$PY" -m pip install --quiet "torch==1.13.1+$DEVICE" "torchvision==0.14.1+$DEVICE" \
    --extra-index-url "https://download.pytorch.org/whl/$DEVICE"

echo "== installing mmcv-full 1.7.x + mmdet 2.28.2 =="
"$PY" -m pip install --quiet -U openmim
"$PY" -m mim install "mmcv-full==1.7.1" || "$PY" -m mim install "mmcv-full==1.7.0" || {
    echo "mmcv-full install failed; fallbacks: mmcv-full 1.6.2, or use the Colab notebook." >&2
    exit 1
}
"$PY" -m pip install --quiet "mmdet==2.28.2" "yapf==0.40.1" gdown opencv-python-headless "numpy<1.24"

echo "== cloning LineFormer (external/, gitignored - no license published, never vendor) =="
[ -d external/LineFormer ] || git clone --depth 1 https://github.com/TheJaeLal/LineFormer external/LineFormer

if ls external/LineFormer/**/*.pth external/LineFormer/*.pth >/dev/null 2>&1; then
    echo "== self-test =="
    "$PY" scripts/lineformer_infer.py --self-test
else
    echo "No checkpoint found. Download iter_3000.pth via the Google Drive link in the"
    echo "LineFormer README, e.g.: $PY -m gdown <GDRIVE_FILE_ID> -O external/LineFormer/iter_3000.pth"
fi
echo "done."
