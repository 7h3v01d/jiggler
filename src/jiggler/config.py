import json
import os
from typing import Dict

class ConfigManager:
    def __init__(self, path: str):
        self.path = path

    def load(self) -> Dict:
        if not os.path.exists(self.path):
            return {'settings': {}, 'pattern_stats': {}}
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
                data.setdefault('settings', {})
                data.setdefault('pattern_stats', {})
                return data
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in config file: {e}") from e
        except Exception as e:
            raise RuntimeError(f"Failed to load config: {e}") from e

    def save(self, data: Dict) -> None:
        existing = self.load()
        existing.update(data)
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(existing, f, indent=2)
        except Exception as e:
            raise RuntimeError(f"Failed to save config: {e}") from e