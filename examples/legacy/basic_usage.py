"""Basic usage example for the v1.0 methodology dispatcher (reference).

For the v1.5.1 production Standard Pipeline, see `examples/example_usage.py`.
"""

from src.methodologies.humanizer import Humanizer

h = Humanizer(config_path="config/config.toml")

text = """
Artificial intelligence has revolutionized the way we approach content creation.
The integration of machine learning algorithms enables unprecedented efficiency
in generating high-quality textual content across various domains.
"""

result = h.process(text, method="translation_chain")
print("Original:")
print(text)
print("\nHumanized:")
print(result.text)
