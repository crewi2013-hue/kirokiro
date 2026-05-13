"""Core authentication module using MSAL for Databricks access."""

import json
import os

import msal
import requests


class DatabricksAuth:
    """Handles authentication to Databricks via Azure AD using MSAL.

    Supports service principal (client credentials) and interactive browser-based
    login flows, with token cache persistence.
    """

    def __init__(self, config):
        """Initialize DatabricksAuth with configuration.

        Args:
            config: Dictionary containing authentication configuration fields.
        """
        self.config = config
        self.tenant_id = config["tenant_id"]
        self.client_id = config["client_id"]
        self.client_secret = (
            os.environ.get("DATABRICKS_CLIENT_SECRET") or config.get("client_secret")
        )
        self.databricks_host = config["databricks_host"]
        self.databricks_scope = config.get(
            "databricks_scope", "2ff814a6-3304-4ab8-85cb-cd0e6f879c1d/.default"
        )
        self.redirect_uri = config.get("redirect_uri", "http://localhost:8400")
        self.token_cache_file = config.get("token_cache_file", ".token_cache.json")
        self.authority = f"https://login.microsoftonline.com/{self.tenant_id}"
        self._token_cache = self._load_token_cache()
        self._access_token = None

    def _load_token_cache(self):
        """Load token cache from file if it exists.

        Returns:
            msal.SerializableTokenCache: The loaded or new token cache.
        """
        cache = msal.SerializableTokenCache()
        if os.path.exists(self.token_cache_file):
            with open(self.token_cache_file, "r", encoding="utf-8") as f:
                cache.deserialize(f.read())
        return cache

    def _save_token_cache(self):
        """Save token cache to file if it has changed.

        Sets file permissions to 600 (owner read/write only) to prevent
        other local users from reading cached tokens.
        """
        if self._token_cache.has_state_changed:
            with open(self.token_cache_file, "w", encoding="utf-8") as f:
                f.write(self._token_cache.serialize())
            os.chmod(self.token_cache_file, 0o600)

    def service_principal_login(self):
        """Authenticate using service principal (client credentials flow).

        Returns:
            dict: Token result containing access_token, or error information.

        Raises:
            ValueError: If client_secret is not configured.
        """
        if not self.client_secret:
            raise ValueError(
                "client_secret is required for service principal login. "
                "Please add it to your config.json."
            )

        app = msal.ConfidentialClientApplication(
            self.client_id,
            authority=self.authority,
            client_credential=self.client_secret,
            token_cache=self._token_cache,
        )

        result = app.acquire_token_for_client(scopes=[self.databricks_scope])

        if "access_token" in result:
            self._access_token = result["access_token"]
            self._save_token_cache()

        return result

    def interactive_login(self):
        """Authenticate using interactive browser-based login.

        Opens a browser window for the user to sign in with their Microsoft account.

        Returns:
            dict: Token result containing access_token, or error information.
        """
        app = msal.PublicClientApplication(
            self.client_id,
            authority=self.authority,
            token_cache=self._token_cache,
        )

        result = app.acquire_token_interactive(
            scopes=[self.databricks_scope],
            redirect_uri=self.redirect_uri,
        )

        if "access_token" in result:
            self._access_token = result["access_token"]
            self._save_token_cache()

        return result

    def silent_login(self):
        """Attempt to acquire token silently from cache.

        Tries to get a token from the cache first. If no cached token is
        available, returns None.

        Returns:
            dict or None: Token result if cache hit, None otherwise.
        """
        app = msal.PublicClientApplication(
            self.client_id,
            authority=self.authority,
            token_cache=self._token_cache,
        )

        accounts = app.get_accounts()
        if accounts:
            result = app.acquire_token_silent(
                scopes=[self.databricks_scope],
                account=accounts[0],
            )
            if result and "access_token" in result:
                self._access_token = result["access_token"]
                self._save_token_cache()
                return result

        return None

    def get_databricks_headers(self):
        """Get HTTP headers with Bearer token for Databricks API calls.

        Returns:
            dict: Headers dictionary with Authorization bearer token.

        Raises:
            RuntimeError: If no access token is available (login first).
        """
        if not self._access_token:
            raise RuntimeError(
                "No access token available. Please login first using "
                "service_principal_login(), interactive_login(), or silent_login()."
            )

        return {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
        }

    def test_connection(self):
        """Test the Databricks connection by listing clusters.

        Returns:
            dict: Response from Databricks clusters/list API.

        Raises:
            RuntimeError: If no access token is available.
            requests.exceptions.RequestException: If the request fails.
        """
        headers = self.get_databricks_headers()
        url = f"{self.databricks_host.rstrip('/')}/api/2.0/clusters/list"
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
