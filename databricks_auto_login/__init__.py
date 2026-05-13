"""Databricks Auto-Login via Microsoft Azure AD (Outlook) Authentication."""

from databricks_auto_login.config import load_config, validate_config
from databricks_auto_login.auth import DatabricksAuth

__all__ = ["load_config", "validate_config", "DatabricksAuth"]
__version__ = "1.0.0"
