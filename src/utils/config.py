"""Configuration utilities."""

import toml


def load_config(path: str = "config/config.toml") -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return toml.load(f)
