"""Load configuration from config.yaml — Project ZRN"""

import yaml
from pathlib import Path

CONFIG_PATH = Path(__file__).parent.parent.parent / "config.yaml"


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"config.yaml not found. Copy config.yaml.example to config.yaml."
        )
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)
