"""CLI entry point for Databricks auto-login tool."""

import argparse
import sys

from databricks_auto_login.config import load_config
from databricks_auto_login.auth import DatabricksAuth


def print_message(id_msg, en_msg):
    """Print bilingual message in Indonesian and English.

    Args:
        id_msg: Message in Indonesian.
        en_msg: Message in English.
    """
    print(f"[ID] {id_msg}")
    print(f"[EN] {en_msg}")
    print()


def cmd_login(args, config):
    """Handle the login command.

    Args:
        args: Parsed command line arguments.
        config: Configuration dictionary.
    """
    auth = DatabricksAuth(config)
    method = args.method

    if method == "auto":
        print_message(
            "Mencoba login otomatis (silent terlebih dahulu)...",
            "Attempting auto login (trying silent first)...",
        )
        result = auth.silent_login()
        if result:
            print_message(
                "Login berhasil menggunakan token cache!",
                "Login successful using cached token!",
            )
            return
        print_message(
            "Token cache tidak tersedia. Mencoba login interaktif...",
            "No cached token available. Trying interactive login...",
        )
        method = "interactive"

    if method == "service_principal":
        print_message(
            "Login menggunakan Service Principal (Client Credentials)...",
            "Logging in using Service Principal (Client Credentials)...",
        )
        try:
            result = auth.service_principal_login()
        except ValueError as e:
            print_message(
                f"Error: {e}",
                f"Error: {e}",
            )
            sys.exit(1)

    elif method == "interactive":
        print_message(
            "Login interaktif - browser akan terbuka untuk autentikasi...",
            "Interactive login - browser will open for authentication...",
        )
        result = auth.interactive_login()

    else:
        print_message(
            f"Metode login tidak dikenal: {method}",
            f"Unknown login method: {method}",
        )
        sys.exit(1)

    if "access_token" in result:
        print_message(
            "Login berhasil! Token telah disimpan.",
            "Login successful! Token has been saved.",
        )
    else:
        error = result.get("error_description", result.get("error", "Unknown error"))
        print_message(
            f"Login gagal: {error}",
            f"Login failed: {error}",
        )
        sys.exit(1)


def cmd_status(config):
    """Handle the status command.

    Args:
        config: Configuration dictionary.
    """
    auth = DatabricksAuth(config)
    result = auth.silent_login()

    if result:
        print_message(
            "Status: Token valid dan tersedia.",
            "Status: Token is valid and available.",
        )
    else:
        print_message(
            "Status: Tidak ada token yang valid. Silakan login terlebih dahulu.",
            "Status: No valid token available. Please login first.",
        )


def cmd_test_connection(config):
    """Handle the test-connection command.

    Args:
        config: Configuration dictionary.
    """
    auth = DatabricksAuth(config)
    result = auth.silent_login()

    if not result:
        print_message(
            "Tidak ada token yang valid. Silakan login terlebih dahulu.",
            "No valid token available. Please login first.",
        )
        sys.exit(1)

    print_message(
        "Menguji koneksi ke Databricks...",
        "Testing connection to Databricks...",
    )

    try:
        response = auth.test_connection()
        clusters = response.get("clusters", [])
        print_message(
            f"Koneksi berhasil! Ditemukan {len(clusters)} cluster.",
            f"Connection successful! Found {len(clusters)} cluster(s).",
        )
    except Exception as e:
        print_message(
            f"Koneksi gagal: {e}",
            f"Connection failed: {e}",
        )
        sys.exit(1)


def create_parser():
    """Create the argument parser for the CLI.

    Returns:
        argparse.ArgumentParser: Configured argument parser.
    """
    parser = argparse.ArgumentParser(
        description="Databricks Auto-Login via Azure AD (Microsoft Entra ID)",
    )
    parser.add_argument(
        "--config",
        default="config.json",
        help="Path to configuration file (default: config.json)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # login command
    login_parser = subparsers.add_parser(
        "login", help="Login to Databricks"
    )
    login_parser.add_argument(
        "--method",
        choices=["interactive", "service_principal", "auto"],
        default="auto",
        help="Login method (default: auto)",
    )

    # status command
    subparsers.add_parser("status", help="Check token status")

    # test-connection command
    subparsers.add_parser(
        "test-connection", help="Test Databricks API connection"
    )

    return parser


def main():
    """Main entry point for the CLI."""
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    try:
        config = load_config(args.config)
    except (FileNotFoundError, ValueError) as e:
        print_message(
            f"Error konfigurasi: {e}",
            f"Configuration error: {e}",
        )
        sys.exit(1)

    if args.command == "login":
        cmd_login(args, config)
    elif args.command == "status":
        cmd_status(config)
    elif args.command == "test-connection":
        cmd_test_connection(config)


if __name__ == "__main__":
    main()
