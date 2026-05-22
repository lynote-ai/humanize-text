"""Batch processing example for the v1.0 methodology dispatcher (reference).

For the v1.5.1 production Standard Pipeline, see `examples/example_usage.py`.
"""

import os
from src.methodologies.humanizer import Humanizer

h = Humanizer(config_path="config/config.toml")

input_dir = "examples/legacy/comparison"
output_dir = "examples/legacy/outputs"
os.makedirs(output_dir, exist_ok=True)

for filename in os.listdir(input_dir):
    if filename.endswith(".txt"):
        with open(os.path.join(input_dir, filename), "r", encoding="utf-8") as f:
            text = f.read()

        result = h.process(text, method="llm_rewrite")

        output_path = os.path.join(output_dir, f"humanized_{filename}")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(result.text)

        print(f"Processed: {filename} -> humanized_{filename}")
