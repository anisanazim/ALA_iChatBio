import os
import yaml

def get_config_value(key: str, default: str = None) -> str:
    """Get configuration value from environment or env.yaml file"""
    value = os.getenv(key)
    if value:
        return value

    try:
        with open("env.yaml", "r") as f:
            config = yaml.safe_load(f) or {}
            return config.get(key, default)
    except FileNotFoundError:
        return default