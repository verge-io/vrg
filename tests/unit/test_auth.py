"""Tests for authentication utilities."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import typer
from pyvergeos.exceptions import AuthenticationError, VergeConnectionError

from verge_cli.auth import AuthMethod, get_client
from verge_cli.config import ProfileConfig


class TestGetClient:
    """Tests for get_client credential resolution and client creation."""

    def test_token_auth_from_config(self) -> None:
        """Token from config should create client with token."""
        config = ProfileConfig(host="test.example.com", token="my-token")

        with patch("verge_cli.auth.VergeClient") as mock_cls:
            mock_cls.return_value = MagicMock()
            client = get_client(config)

            mock_cls.assert_called_once_with(
                host="test.example.com",
                token="my-token",
                verify_ssl=True,
                timeout=30,
            )
            assert client is mock_cls.return_value

    def test_basic_auth_from_config(self) -> None:
        """Username/password from config should create client with basic auth."""
        config = ProfileConfig(host="test.example.com", username="admin", password="secret")

        with patch("verge_cli.auth.VergeClient") as mock_cls:
            mock_cls.return_value = MagicMock()
            client = get_client(config)

            mock_cls.assert_called_once_with(
                host="test.example.com",
                username="admin",
                password="secret",
                verify_ssl=True,
                timeout=30,
            )
            assert client is mock_cls.return_value

    def test_cli_overrides_take_priority(self) -> None:
        """CLI arguments should override config values."""
        config = ProfileConfig(host="config-host.com", token="config-token")

        with patch("verge_cli.auth.VergeClient") as mock_cls:
            mock_cls.return_value = MagicMock()
            get_client(config, host="cli-host.com", token="cli-token")

            mock_cls.assert_called_once_with(
                host="cli-host.com",
                token="cli-token",
                verify_ssl=True,
                timeout=30,
            )

    def test_api_key_used_as_token(self) -> None:
        """API key should be used as token auth."""
        config = ProfileConfig(host="test.example.com", api_key="my-api-key")

        with patch("verge_cli.auth.VergeClient") as mock_cls:
            mock_cls.return_value = MagicMock()
            get_client(config)

            mock_cls.assert_called_once_with(
                host="test.example.com",
                token="my-api-key",
                verify_ssl=True,
                timeout=30,
            )

    def test_cli_api_key_override(self) -> None:
        """CLI --api-key should override config token."""
        config = ProfileConfig(host="test.example.com", token="config-token")

        with patch("verge_cli.auth.VergeClient") as mock_cls:
            mock_cls.return_value = MagicMock()
            get_client(config, api_key="cli-api-key")

            mock_cls.assert_called_once_with(
                host="test.example.com",
                token="cli-api-key",
                verify_ssl=True,
                timeout=30,
            )

    def test_host_strips_https_prefix(self) -> None:
        """Host with https:// prefix should be normalized."""
        config = ProfileConfig(host="https://test.example.com", token="tok")

        with patch("verge_cli.auth.VergeClient") as mock_cls:
            mock_cls.return_value = MagicMock()
            get_client(config)

            assert mock_cls.call_args[1]["host"] == "test.example.com"

    def test_host_strips_http_prefix(self) -> None:
        """Host with http:// prefix should be normalized."""
        config = ProfileConfig(host="http://test.example.com", token="tok")

        with patch("verge_cli.auth.VergeClient") as mock_cls:
            mock_cls.return_value = MagicMock()
            get_client(config)

            assert mock_cls.call_args[1]["host"] == "test.example.com"

    def test_host_strips_trailing_slash(self) -> None:
        """Host with trailing slash should be normalized."""
        config = ProfileConfig(host="https://test.example.com/", token="tok")

        with patch("verge_cli.auth.VergeClient") as mock_cls:
            mock_cls.return_value = MagicMock()
            get_client(config)

            assert mock_cls.call_args[1]["host"] == "test.example.com"

    def test_no_host_non_tty_exits(self) -> None:
        """Missing host in non-TTY should exit with code 3."""
        config = ProfileConfig()

        with patch("sys.stdin") as mock_stdin:
            mock_stdin.isatty.return_value = False
            with pytest.raises(typer.Exit) as exc_info:
                get_client(config)
            assert exc_info.value.exit_code == 3

    def test_no_credentials_non_tty_exits(self) -> None:
        """Missing credentials in non-TTY should exit with code 4."""
        config = ProfileConfig(host="test.example.com")

        with patch("sys.stdin") as mock_stdin:
            mock_stdin.isatty.return_value = False
            with pytest.raises(typer.Exit) as exc_info:
                get_client(config)
            assert exc_info.value.exit_code == 4

    def test_interactive_token_auth(self) -> None:
        """Interactive auth should accept the native token choice."""
        config = ProfileConfig(host="test.example.com")

        with (
            patch("sys.stdin.isatty", return_value=True),
            patch("verge_cli.auth.typer.prompt", side_effect=[AuthMethod.token, "my-token"]),
            patch("verge_cli.auth.VergeClient") as mock_cls,
        ):
            get_client(config)

        mock_cls.assert_called_once_with(
            host="test.example.com",
            token="my-token",
            verify_ssl=True,
            timeout=30,
        )

    def test_authentication_error_exits(self) -> None:
        """AuthenticationError from SDK should exit with code 4."""
        config = ProfileConfig(host="test.example.com", token="bad-token")

        with patch("verge_cli.auth.VergeClient") as mock_cls:
            mock_cls.side_effect = AuthenticationError("Invalid token")
            with pytest.raises(typer.Exit) as exc_info:
                get_client(config)
            assert exc_info.value.exit_code == 4

    def test_connection_error_exits(self) -> None:
        """VergeConnectionError from SDK should exit with code 10."""
        config = ProfileConfig(host="unreachable.example.com", token="tok")

        with patch("verge_cli.auth.VergeClient") as mock_cls:
            mock_cls.side_effect = VergeConnectionError("Connection refused")
            with pytest.raises(typer.Exit) as exc_info:
                get_client(config)
            assert exc_info.value.exit_code == 10

    def test_verify_ssl_passed_through(self) -> None:
        """verify_ssl config should be passed to client."""
        config = ProfileConfig(host="test.example.com", token="tok", verify_ssl=False)

        with patch("verge_cli.auth.VergeClient") as mock_cls:
            mock_cls.return_value = MagicMock()
            get_client(config)

            assert mock_cls.call_args[1]["verify_ssl"] is False

    def test_timeout_passed_through(self) -> None:
        """timeout config should be passed to client."""
        config = ProfileConfig(host="test.example.com", token="tok", timeout=60)

        with patch("verge_cli.auth.VergeClient") as mock_cls:
            mock_cls.return_value = MagicMock()
            get_client(config)

            assert mock_cls.call_args[1]["timeout"] == 60
