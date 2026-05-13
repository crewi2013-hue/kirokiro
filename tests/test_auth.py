"""Unit tests for the auth module.

These tests mock the msal and requests libraries so they can run
without those packages installed.
"""

import sys
import unittest
from unittest.mock import MagicMock, patch, mock_open

# Mock msal and requests at the module level before importing auth
mock_msal = MagicMock()
mock_requests = MagicMock()

sys.modules["msal"] = mock_msal
sys.modules["requests"] = mock_requests

# Now we can import the auth module
from databricks_auto_login.auth import DatabricksAuth


class TestDatabricksAuthInit(unittest.TestCase):
    """Tests for DatabricksAuth initialization."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = {
            "tenant_id": "test-tenant-id",
            "client_id": "test-client-id",
            "client_secret": "test-secret",
            "databricks_host": "https://test.azuredatabricks.net",
            "databricks_scope": "2ff814a6-3304-4ab8-85cb-cd0e6f879c1d/.default",
            "redirect_uri": "http://localhost:8400",
            "token_cache_file": ".token_cache.json",
        }
        mock_msal.SerializableTokenCache.return_value = MagicMock(
            has_state_changed=False
        )

    @patch("os.path.exists", return_value=False)
    def test_init_basic(self, mock_exists):
        """Test basic initialization."""
        auth = DatabricksAuth(self.config)
        self.assertEqual(auth.tenant_id, "test-tenant-id")
        self.assertEqual(auth.client_id, "test-client-id")
        self.assertEqual(auth.client_secret, "test-secret")
        self.assertEqual(auth.databricks_host, "https://test.azuredatabricks.net")
        self.assertEqual(
            auth.authority, "https://login.microsoftonline.com/test-tenant-id"
        )

    @patch("os.path.exists", return_value=False)
    def test_init_without_client_secret(self, mock_exists):
        """Test initialization without client_secret (for interactive login)."""
        config = self.config.copy()
        del config["client_secret"]
        auth = DatabricksAuth(config)
        self.assertIsNone(auth.client_secret)

    @patch.dict("os.environ", {"DATABRICKS_CLIENT_SECRET": "env-secret"})
    @patch("os.path.exists", return_value=False)
    def test_init_client_secret_from_env(self, mock_exists):
        """Test that client_secret is loaded from environment variable."""
        config = self.config.copy()
        del config["client_secret"]
        auth = DatabricksAuth(config)
        self.assertEqual(auth.client_secret, "env-secret")

    @patch.dict("os.environ", {"DATABRICKS_CLIENT_SECRET": "env-secret"})
    @patch("os.path.exists", return_value=False)
    def test_init_env_secret_takes_precedence(self, mock_exists):
        """Test that env variable takes precedence over config file."""
        auth = DatabricksAuth(self.config)
        self.assertEqual(auth.client_secret, "env-secret")


class TestServicePrincipalLogin(unittest.TestCase):
    """Tests for service principal login flow."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = {
            "tenant_id": "test-tenant-id",
            "client_id": "test-client-id",
            "client_secret": "test-secret",
            "databricks_host": "https://test.azuredatabricks.net",
            "databricks_scope": "2ff814a6-3304-4ab8-85cb-cd0e6f879c1d/.default",
            "redirect_uri": "http://localhost:8400",
            "token_cache_file": ".token_cache.json",
        }
        mock_msal.SerializableTokenCache.return_value = MagicMock(
            has_state_changed=False
        )

    @patch("os.path.exists", return_value=False)
    def test_service_principal_login_success(self, mock_exists):
        """Test successful service principal login."""
        mock_app = MagicMock()
        mock_app.acquire_token_for_client.return_value = {
            "access_token": "test-access-token",
            "token_type": "Bearer",
        }
        mock_msal.ConfidentialClientApplication.return_value = mock_app

        auth = DatabricksAuth(self.config)
        result = auth.service_principal_login()

        self.assertEqual(result["access_token"], "test-access-token")
        self.assertEqual(auth._access_token, "test-access-token")
        mock_app.acquire_token_for_client.assert_called_once_with(
            scopes=["2ff814a6-3304-4ab8-85cb-cd0e6f879c1d/.default"]
        )

    @patch("os.path.exists", return_value=False)
    def test_service_principal_login_no_secret(self, mock_exists):
        """Test service principal login fails without client_secret."""
        config = self.config.copy()
        del config["client_secret"]
        auth = DatabricksAuth(config)

        with self.assertRaises(ValueError) as ctx:
            auth.service_principal_login()
        self.assertIn("client_secret", str(ctx.exception))

    @patch("os.path.exists", return_value=False)
    def test_service_principal_login_error(self, mock_exists):
        """Test service principal login with error response."""
        mock_app = MagicMock()
        mock_app.acquire_token_for_client.return_value = {
            "error": "invalid_client",
            "error_description": "Invalid client secret",
        }
        mock_msal.ConfidentialClientApplication.return_value = mock_app

        auth = DatabricksAuth(self.config)
        result = auth.service_principal_login()

        self.assertIn("error", result)
        self.assertIsNone(auth._access_token)


class TestInteractiveLogin(unittest.TestCase):
    """Tests for interactive login flow."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = {
            "tenant_id": "test-tenant-id",
            "client_id": "test-client-id",
            "databricks_host": "https://test.azuredatabricks.net",
            "databricks_scope": "2ff814a6-3304-4ab8-85cb-cd0e6f879c1d/.default",
            "redirect_uri": "http://localhost:8400",
            "token_cache_file": ".token_cache.json",
        }
        mock_msal.SerializableTokenCache.return_value = MagicMock(
            has_state_changed=False
        )

    @patch("os.path.exists", return_value=False)
    def test_interactive_login_success(self, mock_exists):
        """Test successful interactive login."""
        mock_app = MagicMock()
        mock_app.acquire_token_interactive.return_value = {
            "access_token": "interactive-token",
            "token_type": "Bearer",
        }
        mock_msal.PublicClientApplication.return_value = mock_app

        auth = DatabricksAuth(self.config)
        result = auth.interactive_login()

        self.assertEqual(result["access_token"], "interactive-token")
        self.assertEqual(auth._access_token, "interactive-token")


class TestSilentLogin(unittest.TestCase):
    """Tests for silent login (token cache) flow."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = {
            "tenant_id": "test-tenant-id",
            "client_id": "test-client-id",
            "databricks_host": "https://test.azuredatabricks.net",
            "databricks_scope": "2ff814a6-3304-4ab8-85cb-cd0e6f879c1d/.default",
            "redirect_uri": "http://localhost:8400",
            "token_cache_file": ".token_cache.json",
        }
        mock_msal.SerializableTokenCache.return_value = MagicMock(
            has_state_changed=False
        )

    @patch("os.path.exists", return_value=False)
    def test_silent_login_cache_hit(self, mock_exists):
        """Test silent login with cached token."""
        mock_app = MagicMock()
        mock_account = {"username": "user@test.com"}
        mock_app.get_accounts.return_value = [mock_account]
        mock_app.acquire_token_silent.return_value = {
            "access_token": "cached-token",
            "token_type": "Bearer",
        }
        mock_msal.PublicClientApplication.return_value = mock_app

        auth = DatabricksAuth(self.config)
        result = auth.silent_login()

        self.assertIsNotNone(result)
        self.assertEqual(result["access_token"], "cached-token")
        self.assertEqual(auth._access_token, "cached-token")

    @patch("os.path.exists", return_value=False)
    def test_silent_login_no_accounts(self, mock_exists):
        """Test silent login with no cached accounts."""
        mock_app = MagicMock()
        mock_app.get_accounts.return_value = []
        mock_msal.PublicClientApplication.return_value = mock_app

        auth = DatabricksAuth(self.config)
        result = auth.silent_login()

        self.assertIsNone(result)

    @patch("os.path.exists", return_value=False)
    def test_silent_login_token_expired(self, mock_exists):
        """Test silent login when cached token is expired."""
        mock_app = MagicMock()
        mock_account = {"username": "user@test.com"}
        mock_app.get_accounts.return_value = [mock_account]
        mock_app.acquire_token_silent.return_value = None
        mock_msal.PublicClientApplication.return_value = mock_app

        auth = DatabricksAuth(self.config)
        result = auth.silent_login()

        self.assertIsNone(result)


class TestGetDatabricksHeaders(unittest.TestCase):
    """Tests for get_databricks_headers method."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = {
            "tenant_id": "test-tenant-id",
            "client_id": "test-client-id",
            "databricks_host": "https://test.azuredatabricks.net",
            "databricks_scope": "2ff814a6-3304-4ab8-85cb-cd0e6f879c1d/.default",
            "redirect_uri": "http://localhost:8400",
            "token_cache_file": ".token_cache.json",
        }
        mock_msal.SerializableTokenCache.return_value = MagicMock(
            has_state_changed=False
        )

    @patch("os.path.exists", return_value=False)
    def test_get_headers_with_token(self, mock_exists):
        """Test getting headers when token is available."""
        mock_app = MagicMock()
        mock_app.acquire_token_for_client.return_value = {
            "access_token": "test-token",
        }
        mock_msal.ConfidentialClientApplication.return_value = mock_app

        config = self.config.copy()
        config["client_secret"] = "test-secret"
        auth = DatabricksAuth(config)
        auth.service_principal_login()

        headers = auth.get_databricks_headers()
        self.assertEqual(headers["Authorization"], "Bearer test-token")
        self.assertEqual(headers["Content-Type"], "application/json")

    @patch("os.path.exists", return_value=False)
    def test_get_headers_without_token(self, mock_exists):
        """Test getting headers raises error when no token."""
        auth = DatabricksAuth(self.config)

        with self.assertRaises(RuntimeError) as ctx:
            auth.get_databricks_headers()
        self.assertIn("No access token", str(ctx.exception))


class TestTestConnection(unittest.TestCase):
    """Tests for test_connection method."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = {
            "tenant_id": "test-tenant-id",
            "client_id": "test-client-id",
            "client_secret": "test-secret",
            "databricks_host": "https://test.azuredatabricks.net",
            "databricks_scope": "2ff814a6-3304-4ab8-85cb-cd0e6f879c1d/.default",
            "redirect_uri": "http://localhost:8400",
            "token_cache_file": ".token_cache.json",
        }
        mock_msal.SerializableTokenCache.return_value = MagicMock(
            has_state_changed=False
        )

    @patch("os.path.exists", return_value=False)
    def test_test_connection_success(self, mock_exists):
        """Test successful connection test."""
        mock_app = MagicMock()
        mock_app.acquire_token_for_client.return_value = {
            "access_token": "test-token",
        }
        mock_msal.ConfidentialClientApplication.return_value = mock_app

        mock_response = MagicMock()
        mock_response.json.return_value = {"clusters": [{"cluster_id": "123"}]}
        mock_response.raise_for_status = MagicMock()
        mock_requests.get.return_value = mock_response

        auth = DatabricksAuth(self.config)
        auth.service_principal_login()
        result = auth.test_connection()

        self.assertEqual(len(result["clusters"]), 1)
        mock_requests.get.assert_called_once_with(
            "https://test.azuredatabricks.net/api/2.0/clusters/list",
            headers=auth.get_databricks_headers(),
            timeout=30,
        )


class TestTokenCachePersistence(unittest.TestCase):
    """Tests for token cache file operations."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = {
            "tenant_id": "test-tenant-id",
            "client_id": "test-client-id",
            "client_secret": "test-secret",
            "databricks_host": "https://test.azuredatabricks.net",
            "databricks_scope": "2ff814a6-3304-4ab8-85cb-cd0e6f879c1d/.default",
            "redirect_uri": "http://localhost:8400",
            "token_cache_file": ".token_cache.json",
        }

    @patch("builtins.open", mock_open(read_data='{"cached": "data"}'))
    @patch("os.path.exists", return_value=True)
    def test_load_existing_cache(self, mock_exists):
        """Test loading an existing token cache file."""
        mock_cache = MagicMock(has_state_changed=False)
        mock_msal.SerializableTokenCache.return_value = mock_cache

        auth = DatabricksAuth(self.config)
        mock_cache.deserialize.assert_called_once_with('{"cached": "data"}')

    @patch("os.path.exists", return_value=False)
    def test_new_cache_when_no_file(self, mock_exists):
        """Test creating new cache when file does not exist."""
        mock_cache = MagicMock(has_state_changed=False)
        mock_msal.SerializableTokenCache.return_value = mock_cache

        auth = DatabricksAuth(self.config)
        mock_cache.deserialize.assert_not_called()

    @patch("os.chmod")
    @patch("builtins.open", mock_open())
    @patch("os.path.exists", return_value=False)
    def test_save_cache_sets_permissions(self, mock_exists, mock_chmod):
        """Test that saving token cache sets file permissions to 600."""
        mock_cache = MagicMock(has_state_changed=True)
        mock_cache.serialize.return_value = '{"token": "data"}'
        mock_msal.SerializableTokenCache.return_value = mock_cache

        auth = DatabricksAuth(self.config)
        auth._save_token_cache()

        mock_chmod.assert_called_once_with(".token_cache.json", 0o600)


if __name__ == "__main__":
    unittest.main()
