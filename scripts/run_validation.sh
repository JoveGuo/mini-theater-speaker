#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

python3 scripts/generate_test_tones.py --with-raw
python3 scripts/validate_config.py \
  configs/2.1.yml \
  configs/2.1.stdin.yml \
  configs/2.1.file.yml \
  configs/2.1.usb.yml
python3 -m unittest discover -s tests -p "test_*.py"
