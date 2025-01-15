import yaml
from pathlib import Path

class Config:
    @staticmethod
    def load_config() -> dict:
        config_path = Path("config/config.yaml")
        with open(config_path) as f:
            return yaml.safe_load(f) 