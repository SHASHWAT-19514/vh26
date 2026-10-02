#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.lock
mkdir -p data/inbox data/datasets data/tmp logs benchmarks/results
python -m abhedya init
printf 'Setup complete. Run ./scripts/run.sh\n'
