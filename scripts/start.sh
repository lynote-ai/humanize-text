#!/bin/bash
echo "Starting AI-Humanizer..."
pip install -r requirements.txt
python -m src.humanizer "$@"
