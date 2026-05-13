"""Unit tests for the config module."""

import json
import os
import tempfile
import unittest
from unittest.mock import patch, mock_open

from databricks_auto_login.config import load_config, validate_config, DEFAULTS


class TestValidateConfig(unittest.TestCase):
    """Tests for the validate_config function."""

    def test_valid_config_all_fields(self):
        """Test validation passes with all required fields."""
        config = {
            "tenant_id": "test-tenant-id",
            "client_id": "test-client-id",
            "databricks_host": "https://test.azuredatabricks.net",
        }
        # Should not raise
        validate_config(config)

    def test_missing_tenant_id(self):
        """Test validation fails when tenant_id is missing."""
        config = {
            "client_id": "test-client-id",
            "databricks_host": "https://test.azuredatabricks.net",
        }
        with self.assertRaises(ValueError) as ctx:
            validate_config(config)
        self.assertIn("tenant_id", str(ctx.exception))

    def test_missing_client_id(self):
        """Test validation fails when client_id is missing."""
        config = {
            "tenant_id": "test-tenant-id",
            "databricks_host": "https://test.azuredatabricks.net",
        }
        with self.assertRaises(ValueError) as ctx:
            validate_config(config)
        self.assertIn("client_id", str(ctx.exception))

    def test_missing_databricks_host(self):
        """Test validation fails when databricks_host is missing."""
        config = {
            "tenant_id": "test-tenant-id",
            "client_id": "test-client-id",
        }
        with self.assertRaises(ValueError) as ctx:
            validate_config(config)
        self.assertIn("databricks_host", str(ctx.exception))

    def test_missing_multiple_fields(self):
        """Test validation reports all missing fields."""
        config = {}
        with self.assertRaises(ValueError) as ctx:
            validate_config(config)
        error_msg = str(ctx.exception)
        self.assertIn("tenant_id", error_msg)
        self.assertIn("client_id", error_msg)
        self.assertIn("databricks_host", error_msg)

    def test_empty_field_value(self):
        """Test validation fails when required field is empty string."""
        config = {
            "tenant_id": "",
            "client_id": "test-client-id",
            "databricks_host": "https://test.azuredatabricks.net",
        }
        with self.assertRaises(ValueError) as ctx:
            validate_config(config)
        self.assertIn("tenant_id", str(ctx.exception))


class TestLoadConfig(unittest.TestCase):
    """Tests for the load_config function."""

    def test_file_not_found(self):
        """Test that FileNotFoundError is raised when config file doesn't exist."""
        with self.assertRaises(FileNotFoundError):
            load_config("/nonexistent/path/config.json")

    def test_load_valid_config(self):
        """Test loading a valid configuration file."""
        config_data = {
            "tenant_id": "test-tenant-id",
            "client_id": "test-client-id",
            "databricks_host": "https://test.azuredatabricks.net",
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(config_data, f)
            temp_path = f.name

        try:
            result = load_config(temp_path)
            self.assertEqual(result["tenant_id"], "test-tenant-id")
            self.assertEqual(result["client_id"], "test-client-id")
            self.assertEqual(result["databricks_host"], "https://test.azuredatabricks.net")
        finally:
            os.unlink(temp_path)

    def test_defaults_applied(self):
        """Test that default values are applied for optional fields."""
        config_data = {
            "tenant_id": "test-tenant-id",
            "client_id": "test-client-id",
            "databricks_host": "https://test.azuredatabricks.net",
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(config_data, f)
            temp_path = f.name

        try:
            result = load_config(temp_path)
            self.assertEqual(
                result["databricks_scope"],
                "2ff814a6-3304-4ab8-85cb-cd0e6f879c1d/.default",
            )
            self.assertEqual(result["redirect_uri"], "http://localhost:8400")
            self.assertEqual(result["token_cache_file"], ".token_cache.json")
        finally:
            os.unlink(temp_path)

    def test_custom_values_not_overridden(self):
        """Test that custom values are not overridden by defaults."""
        config_data = {
            "tenant_id": "test-tenant-id",
            "client_id": "test-client-id",
            "databricks_host": "https://test.azuredatabricks.net",
            "redirect_uri": "http://localhost:9000",
            "token_cache_file": "custom_cache.json",
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(config_data, f)
            temp_path = f.name

        try:
            result = load_config(temp_path)
            self.assertEqual(result["redirect_uri"], "http://localhost:9000")
            self.assertEqual(result["token_cache_file"], "custom_cache.json")
        finally:
            os.unlink(temp_path)

    def test_invalid_json(self):
        """Test that invalid JSON raises an error."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            f.write("not valid json {{{")
            temp_path = f.name

        try:
            with self.assertRaises(json.JSONDecodeError):
                load_config(temp_path)
        finally:
            os.unlink(temp_path)


if __name__ == "__main__":
    unittest.main()
