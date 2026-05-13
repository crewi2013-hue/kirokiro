"""Configuration loader for Databricks auto-login."""

import json
import os


REQUIRED_FIELDS = ["tenant_id", "client_id", "databricks_host"]

DEFAULTS = {
    "databricks_scope": "2ff814a6-3304-4ab8-85cb-cd0e6f879c1d/.default",
    "redirect_uri": "http://localhost:8400",
    "token_cache_file": ".token_cache.json",
}


def load_config(config_path="config.json"):
    """Load configuration from a JSON file.

    Args:
        config_path: Path to the configuration JSON file.

    Returns:
        dict: Configuration dictionary with all fields populated.

    Raises:
        FileNotFoundError: If the configuration file does not exist.
        json.JSONDecodeError: If the configuration file is not valid JSON.
        ValueError: If required fields are missing.
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(
            f"Configuration file not found: {config_path}. "
            "Please copy config.example.json to config.json and fill in your values."
        )

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    validate_config(config)

    # Apply defaults for optional fields
    for key, default_value in DEFAULTS.items():
        if key not in config or not config[key]:
            config[key] = default_value

    return config


def validate_config(config):
    """Validate that required configuration fields are present.

    Args:
        config: Configuration dictionary to validate.

    Raises:
        ValueError: If required fields are missing or empty.
    """
    missing_fields = []
    for field in REQUIRED_FIELDS:
        if field not in config or not config[field]:
            missing_fields.append(field)

    if missing_fields:
        raise ValueError(
            f"Missing required configuration fields: {', '.join(missing_fields)}"
        )
