import os
from typing import Any

import yaml


def update_llm_credentials(metadata: dict[str, Any] | None):
    if metadata is None:
        return

    if os.getenv("USE_LLM_PROXY") == "true":
        match metadata:
            case {"https://ichatbio.org/a2a/v1": {"temporary_llm_key": llm_key}}:
                os.environ["OPENAI_API_KEY"] = llm_key

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