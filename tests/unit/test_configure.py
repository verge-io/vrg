"""Tests for configure commands."""

from __future__ import annotations

from unittest.mock import patch

from verge_cli.cli import app
from verge_cli.config import Config, ProfileConfig


class TestConfigureShow:
    """Tests for configure show command."""

    def test_show_effective_config(self, cli_runner, mock_client) -> None:
        """configure show (no --profile) should show effective config."""
        config = ProfileConfig(
            host="test.example.com",
            token="abcd1234efgh5678",
            verify_ssl=True,
            output="table",
            timeout=30,
        )
        with patch("verge_cli.commands.configure.get_effective_config", return_value=config):
            result = cli_runner.invoke(app, ["configure", "show"])

        assert result.exit_code == 0
        assert "test.example.com" in result.output

    def test_show_specific_profile(self, cli_runner, mock_client) -> None:
        """configure show --profile dev should show that profile."""
        dev_profile = ProfileConfig(
            host="dev.example.com",
            username="admin",
            password="secret",
            verify_ssl=False,
        )
        config = Config(
            default=ProfileConfig(),
            profiles={"dev": dev_profile},
        )
        with patch("verge_cli.commands.configure.load_config", return_value=config):
            result = cli_runner.invoke(app, ["configure", "show", "--profile", "dev"])

        assert result.exit_code == 0
        assert "dev.example.com" in result.output

    def test_show_nonexistent_profile_exits(self, cli_runner, mock_client) -> None:
        """configure show --profile nonexistent should exit with error."""
        config = Config(default=ProfileConfig(), profiles={})
        with patch("verge_cli.commands.configure.load_config", return_value=config):
            result = cli_runner.invoke(app, ["configure", "show", "--profile", "nonexistent"])

        assert result.exit_code == 3

    def test_show_masks_secrets(self, cli_runner, mock_client) -> None:
        """Secrets should be masked by default."""
        config = ProfileConfig(
            host="test.example.com",
            token="abcdefghijklmnop",
            verify_ssl=True,
        )
        with patch("verge_cli.commands.configure.get_effective_config", return_value=config):
            result = cli_runner.invoke(app, ["configure", "show"])

        assert result.exit_code == 0
        # Token should be masked (first 4 ... last 4)
        assert "abcdefghijklmnop" not in result.output

    def test_show_secrets_flag(self, cli_runner, mock_client) -> None:
        """--show-secrets should reveal values."""
        config = ProfileConfig(
            host="test.example.com",
            token="abcdefghijklmnop",
            verify_ssl=True,
        )
        with patch("verge_cli.commands.configure.get_effective_config", return_value=config):
            result = cli_runner.invoke(app, ["configure", "show", "--show-secrets"])

        assert result.exit_code == 0
        assert "abcdefghijklmnop" in result.output

    def test_show_short_secret_fully_masked(self, cli_runner, mock_client) -> None:
        """Short secrets (<=8 chars) should be fully masked."""
        config = ProfileConfig(
            host="test.example.com",
            token="short",
            verify_ssl=True,
        )
        with patch("verge_cli.commands.configure.get_effective_config", return_value=config):
            result = cli_runner.invoke(app, ["configure", "show"])

        assert result.exit_code == 0
        assert "short" not in result.output
        assert "********" in result.output


class TestConfigureList:
    """Tests for configure list command."""

    def test_list_profiles(self, cli_runner, mock_client) -> None:
        """configure list should show all profiles."""
        config = Config(
            default=ProfileConfig(host="default.example.com", token="tok"),
            profiles={
                "dev": ProfileConfig(host="dev.example.com", username="admin"),
                "staging": ProfileConfig(host="staging.example.com", api_key="key"),
            },
        )
        with patch("verge_cli.commands.configure.load_config", return_value=config):
            result = cli_runner.invoke(app, ["configure", "list"])

        assert result.exit_code == 0
        assert "default" in result.output
        assert "dev" in result.output
        assert "staging" in result.output

    def test_list_shows_auth_types(self, cli_runner, mock_client) -> None:
        """configure list should display correct auth types."""
        config = Config(
            default=ProfileConfig(host="a.com", token="tok"),
            profiles={
                "basic": ProfileConfig(host="b.com", username="admin"),
                "apikey": ProfileConfig(host="c.com", api_key="key"),
                "empty": ProfileConfig(host="d.com"),
            },
        )
        with patch("verge_cli.commands.configure.load_config", return_value=config):
            result = cli_runner.invoke(app, ["configure", "list"])

        assert result.exit_code == 0
        assert "Bearer token" in result.output
        assert "Basic auth" in result.output
        assert "API key" in result.output


class TestConfigureSetup:
    """Tests for configure setup (interactive)."""

    def test_setup_with_token(self, cli_runner, mock_client) -> None:
        """configure setup with token auth should save config."""
        config = Config(default=ProfileConfig(), profiles={})
        with (
            patch("verge_cli.commands.configure.load_config", return_value=config),
            patch("verge_cli.commands.configure.save_config") as mock_save,
        ):
            result = cli_runner.invoke(
                app,
                ["configure", "setup"],
                input="test.example.com\nmy-token\nyes\nyaml\ntable\n30\n",
            )

        assert result.exit_code == 0
        assert "table, wide, json, csv" in result.output
        assert "Error: yaml" in result.output
        assert "saved" in result.output.lower()
        mock_save.assert_called_once()

    def test_setup_named_profile(self, cli_runner, mock_client) -> None:
        """configure setup --profile dev should save to named profile."""
        config = Config(default=ProfileConfig(), profiles={})
        with (
            patch("verge_cli.commands.configure.load_config", return_value=config),
            patch("verge_cli.commands.configure.save_config") as mock_save,
        ):
            result = cli_runner.invoke(
                app,
                ["configure", "setup", "--profile", "dev"],
                input="dev.example.com\ndev-token\nyes\ntable\n30\n",
            )

        assert result.exit_code == 0
        mock_save.assert_called_once()
        saved_config = mock_save.call_args[0][0]
        assert "dev" in saved_config.profiles
