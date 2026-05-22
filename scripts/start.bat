@echo off
REM Humanize-Text v1.5.1 - Standard Pipeline launcher
REM Usage: scripts\start.bat --input "Your text here" --target en [--verbose]
echo Starting humanize-text Standard Pipeline...
pip install -q -r requirements.txt
python -m src.standard.pipeline %*
