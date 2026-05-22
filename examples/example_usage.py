"""Example: Run the Standard humanization pipeline."""

import toml
from src.standard import run_standard_pipeline

config = toml.load("config/config.toml")

text = """
The implementation of artificial intelligence in educational settings has
fundamentally transformed the landscape of modern pedagogy. Machine learning
algorithms have demonstrated remarkable capabilities in personalizing learning
experiences and providing real-time feedback mechanisms.
"""

result = run_standard_pipeline(text, config, target_lang="en")

print("Humanized text:")
print(result["result"])
print(f"\nProcessing time: {result['processing_time_ms']}ms")
print("\nSteps:")
for step in result["steps"]:
    print(f"  {step['step']}: {step['engine']} | {step['direction']} | {step['length']} chars")
