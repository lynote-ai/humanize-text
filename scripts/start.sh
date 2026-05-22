#!/bin/bash
# Humanize-Text v1.5.1 — Standard Pipeline launcher
# Usage: ./scripts/start.sh --input "Your text here" --target en [--verbose]
echo "Starting humanize-text Standard Pipeline..."
pip install -q -r requirements.txt
python -m src.standard.pipeline "$@"
