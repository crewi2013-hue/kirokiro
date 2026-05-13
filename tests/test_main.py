"""Unit tests for the main CLI module."""

import sys
import unittest
from unittest.mock import MagicMock, patch, call
from io import StringIO

# Mock msal and requests at the module level before importing main
if "msal" not in sys.modules:
    sys.modules["msal"] = MagicMock()
if "requests" not in sys.modules:
    sys.modules["requests"] = MagicMock()

from databricks_auto_login.main import (
    create_parser,
    cmd_login,
    cmd_status,
    cmd_test_connection,
    print_message,
    main,
)


class TestCreateParser(unittest.TestCase):
    """Tests for the create_parser function."""

    def test_parser_has_config_argument(self):
        """Test that parser accepts --config argument."""
        parser = create_parser()
        args = parser.parse_args(["--config", "custom.json", "login"])
        self.assertEqual(args.config, "custom.json")

    def test_parser_default_config(self):
        """Test that parser default config is config.json."""
        parser = create_parser()
        args = parser.parse_args(["login"])
        self.assertEqual(args.config, "config.json")

    def test_parser_login_command(self):
        """Test that parser recognizes login command."""
        parser = create_parser()
        args = parser.parse_args(["login"])
        self.assertEqual(args.command, "login")
        self.assertEqual(args.method, "auto")

    def test_parser_login_method_choices(self):
        """Test that login command accepts method choices."""
        parser = create_parser()
        for method in ["interactive", "service_principal", "auto"]:
            args = parser.parse_args(["login", "--method", method])
            self.assertEqual(args.method, method)

    def test_parser_status_command(self):
        """Test that parser recognizes status command."""
        parser = create_parser()
        args = parser.parse_args(["status"])
        self.assertEqual(args.command, "status")

    def test_parser_test_connection_command(self):
        """Test that parser recognizes test-connection command."""
        parser = create_parser()
        args = parser.parse_args(["test-connection"])
        self.assertEqual(args.command, "test-connection")

    def test_parser_no_command(self):
        """Test that parser with no command sets command to None."""
        parser = create_parser()
        args = parser.parse_args([])
        self.assertIsNone(args.command)


class TestPrintMessage(unittest.TestCase):
    """Tests for the print_message function."""

    @patch("sys.stdout", new_callable=StringIO)
    def test_bilingual_output(self, mock_stdout):
        """Test that print_message outputs both languages."""
        print_message("Pesan Indonesia", "English message")
        output = mock_stdout.getvalue()
        self.assertIn("[ID] Pesan Indonesia", output)
        self.assertIn("[EN] English message", output)


class TestCmdLogin(unittest.TestCase):
    """Tests for the cmd_login command function."""

    def _make_args(self, method="auto"):
        """Create mock args object."""
        args = MagicMock()
        args.method = method
        return args

    def _make_config(self):
        """Create a test config dictionary."""
        return {
            "tenant_id": "test-tenant",
            "client_id": "test-client",
            "client_secret": "test-secret",
            "databricks_host": "https://test.azuredatabricks.net",
            "databricks_scope": "2ff814a6-3304-4ab8-85cb-cd0e6f879c1d/.default",
            "redirect_uri": "http://localhost:8400",
            "token_cache_file": ".token_cache.json",
        }

    @patch("databricks_auto_login.main.DatabricksAuth")
    @patch("sys.stdout", new_callable=StringIO)
    def test_login_auto_silent_success(self, mock_stdout, MockAuth):
        """Test auto login succeeds with silent token."""
        mock_auth = MockAuth.return_value
        mock_auth.silent_login.return_value = {"access_token": "cached-token"}

        cmd_login(self._make_args("auto"), self._make_config())

        mock_auth.silent_login.assert_called_once()
        output = mock_stdout.getvalue()
        self.assertIn("Login successful using cached token", output)

    @patch("databricks_auto_login.main.DatabricksAuth")
    @patch("sys.stdout", new_callable=StringIO)
    def test_login_auto_falls_back_to_interactive(self, mock_stdout, MockAuth):
        """Test auto login falls back to interactive when no cache."""
        mock_auth = MockAuth.return_value
        mock_auth.silent_login.return_value = None
        mock_auth.interactive_login.return_value = {"access_token": "new-token"}

        cmd_login(self._make_args("auto"), self._make_config())

        mock_auth.silent_login.assert_called_once()
        mock_auth.interactive_login.assert_called_once()
        output = mock_stdout.getvalue()
        self.assertIn("Login successful", output)

    @patch("databricks_auto_login.main.DatabricksAuth")
    @patch("sys.stdout", new_callable=StringIO)
    def test_login_service_principal_success(self, mock_stdout, MockAuth):
        """Test service principal login success."""
        mock_auth = MockAuth.return_value
        mock_auth.service_principal_login.return_value = {
            "access_token": "sp-token"
        }

        cmd_login(self._make_args("service_principal"), self._make_config())

        mock_auth.service_principal_login.assert_called_once()
        output = mock_stdout.getvalue()
        self.assertIn("Login successful", output)

    @patch("databricks_auto_login.main.DatabricksAuth")
    @patch("sys.stdout", new_callable=StringIO)
    def test_login_service_principal_no_secret(self, mock_stdout, MockAuth):
        """Test service principal login fails without secret."""
        mock_auth = MockAuth.return_value
        mock_auth.service_principal_login.side_effect = ValueError(
            "client_secret is required"
        )

        with self.assertRaises(SystemExit) as ctx:
            cmd_login(self._make_args("service_principal"), self._make_config())
        self.assertEqual(ctx.exception.code, 1)

    @patch("databricks_auto_login.main.DatabricksAuth")
    @patch("sys.stdout", new_callable=StringIO)
    def test_login_interactive_success(self, mock_stdout, MockAuth):
        """Test interactive login success."""
        mock_auth = MockAuth.return_value
        mock_auth.interactive_login.return_value = {
            "access_token": "interactive-token"
        }

        cmd_login(self._make_args("interactive"), self._make_config())

        mock_auth.interactive_login.assert_called_once()
        output = mock_stdout.getvalue()
        self.assertIn("Login successful", output)

    @patch("databricks_auto_login.main.DatabricksAuth")
    @patch("sys.stdout", new_callable=StringIO)
    def test_login_error_response(self, mock_stdout, MockAuth):
        """Test login with error in token response."""
        mock_auth = MockAuth.return_value
        mock_auth.interactive_login.return_value = {
            "error": "invalid_grant",
            "error_description": "Token expired",
        }

        with self.assertRaises(SystemExit) as ctx:
            cmd_login(self._make_args("interactive"), self._make_config())
        self.assertEqual(ctx.exception.code, 1)
        output = mock_stdout.getvalue()
        self.assertIn("Login failed", output)


class TestCmdStatus(unittest.TestCase):
    """Tests for the cmd_status command function."""

    def _make_config(self):
        return {
            "tenant_id": "test-tenant",
            "client_id": "test-client",
            "databricks_host": "https://test.azuredatabricks.net",
            "databricks_scope": "2ff814a6-3304-4ab8-85cb-cd0e6f879c1d/.default",
            "redirect_uri": "http://localhost:8400",
            "token_cache_file": ".token_cache.json",
        }

    @patch("databricks_auto_login.main.DatabricksAuth")
    @patch("sys.stdout", new_callable=StringIO)
    def test_status_valid_token(self, mock_stdout, MockAuth):
        """Test status when token is valid."""
        mock_auth = MockAuth.return_value
        mock_auth.silent_login.return_value = {"access_token": "valid-token"}

        cmd_status(self._make_config())

        output = mock_stdout.getvalue()
        self.assertIn("Token is valid", output)

    @patch("databricks_auto_login.main.DatabricksAuth")
    @patch("sys.stdout", new_callable=StringIO)
    def test_status_no_token(self, mock_stdout, MockAuth):
        """Test status when no valid token."""
        mock_auth = MockAuth.return_value
        mock_auth.silent_login.return_value = None

        cmd_status(self._make_config())

        output = mock_stdout.getvalue()
        self.assertIn("No valid token", output)


class TestCmdTestConnection(unittest.TestCase):
    """Tests for the cmd_test_connection command function."""

    def _make_config(self):
        return {
            "tenant_id": "test-tenant",
            "client_id": "test-client",
            "databricks_host": "https://test.azuredatabricks.net",
            "databricks_scope": "2ff814a6-3304-4ab8-85cb-cd0e6f879c1d/.default",
            "redirect_uri": "http://localhost:8400",
            "token_cache_file": ".token_cache.json",
        }

    @patch("databricks_auto_login.main.DatabricksAuth")
    @patch("sys.stdout", new_callable=StringIO)
    def test_connection_no_token(self, mock_stdout, MockAuth):
        """Test connection fails when no token."""
        mock_auth = MockAuth.return_value
        mock_auth.silent_login.return_value = None

        with self.assertRaises(SystemExit) as ctx:
            cmd_test_connection(self._make_config())
        self.assertEqual(ctx.exception.code, 1)
        output = mock_stdout.getvalue()
        self.assertIn("No valid token", output)

    @patch("databricks_auto_login.main.DatabricksAuth")
    @patch("sys.stdout", new_callable=StringIO)
    def test_connection_success(self, mock_stdout, MockAuth):
        """Test successful connection test."""
        mock_auth = MockAuth.return_value
        mock_auth.silent_login.return_value = {"access_token": "token"}
        mock_auth.test_connection.return_value = {
            "clusters": [{"cluster_id": "c1"}, {"cluster_id": "c2"}]
        }

        cmd_test_connection(self._make_config())

        mock_auth.test_connection.assert_called_once()
        output = mock_stdout.getvalue()
        self.assertIn("Connection successful", output)
        self.assertIn("2", output)

    @patch("databricks_auto_login.main.DatabricksAuth")
    @patch("sys.stdout", new_callable=StringIO)
    def test_connection_failure(self, mock_stdout, MockAuth):
        """Test connection test when API call fails."""
        mock_auth = MockAuth.return_value
        mock_auth.silent_login.return_value = {"access_token": "token"}
        mock_auth.test_connection.side_effect = Exception("Connection refused")

        with self.assertRaises(SystemExit) as ctx:
            cmd_test_connection(self._make_config())
        self.assertEqual(ctx.exception.code, 1)
        output = mock_stdout.getvalue()
        self.assertIn("Connection failed", output)


class TestMain(unittest.TestCase):
    """Tests for the main entry point."""

    @patch("databricks_auto_login.main.load_config")
    @patch("databricks_auto_login.main.cmd_login")
    @patch("sys.argv", ["prog", "login", "--method", "interactive"])
    def test_main_dispatches_login(self, mock_cmd_login, mock_load_config):
        """Test that main dispatches to cmd_login."""
        mock_load_config.return_value = {"tenant_id": "t", "client_id": "c", "databricks_host": "https://h"}
        main()
        mock_cmd_login.assert_called_once()

    @patch("databricks_auto_login.main.load_config")
    @patch("databricks_auto_login.main.cmd_status")
    @patch("sys.argv", ["prog", "status"])
    def test_main_dispatches_status(self, mock_cmd_status, mock_load_config):
        """Test that main dispatches to cmd_status."""
        mock_load_config.return_value = {"tenant_id": "t", "client_id": "c", "databricks_host": "https://h"}
        main()
        mock_cmd_status.assert_called_once()

    @patch("databricks_auto_login.main.load_config")
    @patch("databricks_auto_login.main.cmd_test_connection")
    @patch("sys.argv", ["prog", "test-connection"])
    def test_main_dispatches_test_connection(self, mock_cmd_test, mock_load_config):
        """Test that main dispatches to cmd_test_connection."""
        mock_load_config.return_value = {"tenant_id": "t", "client_id": "c", "databricks_host": "https://h"}
        main()
        mock_cmd_test.assert_called_once()

    @patch("sys.stdout", new_callable=StringIO)
    @patch("sys.argv", ["prog"])
    def test_main_no_command_shows_help(self, mock_stdout):
        """Test that main with no command shows help and exits."""
        with self.assertRaises(SystemExit) as ctx:
            main()
        self.assertEqual(ctx.exception.code, 0)

    @patch("databricks_auto_login.main.load_config")
    @patch("sys.stdout", new_callable=StringIO)
    @patch("sys.argv", ["prog", "login"])
    def test_main_config_error(self, mock_stdout, mock_load_config):
        """Test that main handles config errors gracefully."""
        mock_load_config.side_effect = FileNotFoundError("config.json not found")

        with self.assertRaises(SystemExit) as ctx:
            main()
        self.assertEqual(ctx.exception.code, 1)
        output = mock_stdout.getvalue()
        self.assertIn("Configuration error", output)


if __name__ == "__main__":
    unittest.main()
