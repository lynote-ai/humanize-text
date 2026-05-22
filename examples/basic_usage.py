"""Basic usage example for AI-Humanizer."""

from src.humanizer import Humanizer

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
