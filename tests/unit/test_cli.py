"""Unit tests for CLI commands."""

from __future__ import annotations

from unittest.mock import patch

from typer.testing import CliRunner

from verge_cli import __version__
from verge_cli.cli import app
from verge_cli.config import ProfileConfig


class TestCliBasic:
    """Basic CLI tests."""

    def test_version_flag(self, cli_runner: CliRunner) -> None:
        """Test --version flag."""
        result = cli_runner.invoke(app, ["--version"])

        assert result.exit_code == 0
        assert __version__ in result.stdout

    def test_help_flag(self, cli_runner: CliRunner) -> None:
        """Test --help flag."""
        result = cli_runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        assert "CLI for managing VergeOS infrastructure" in result.stdout
        assert "configure" in result.stdout
        assert "vm" in result.stdout
        assert "network" in result.stdout
        assert "system" in result.stdout
        assert "tenant" in result.stdout
        assert "cluster" in result.stdout
        assert "node" in result.stdout
        assert "storage" in result.stdout

    def test_no_args_shows_help(self, cli_runner: CliRunner) -> None:
        """Test that running without args shows help."""
        result = cli_runner.invoke(app, [])

        # Typer returns exit code 0 for --help but 2 for no_args_is_help
        # Both show help text, so we just verify the help is shown
        assert "Usage:" in result.stdout


class TestConfigureCommands:
    """Tests for configure commands."""

    def test_configure_help(self, cli_runner: CliRunner) -> None:
        """Test configure --help."""
        result = cli_runner.invoke(app, ["configure", "--help"])

        assert result.exit_code == 0
        assert "setup" in result.stdout
        assert "show" in result.stdout
        assert "list" in result.stdout

    def test_configure_show_no_config(self, cli_runner: CliRunner) -> None:
        """Test configure show with no config file."""
        result = cli_runner.invoke(app, ["configure", "show"])

        assert result.exit_code == 0
        assert "Effective Configuration" in result.stdout

    def test_configure_list_no_config(self, cli_runner: CliRunner) -> None:
        """Test configure list with no config file."""
        result = cli_runner.invoke(app, ["configure", "list"])

        assert result.exit_code == 0
        assert "Profiles" in result.stdout
        assert "default" in result.stdout


class TestVmCommands:
    """Tests for VM commands."""

    def test_vm_help(self, cli_runner: CliRunner) -> None:
        """Test vm --help."""
        result = cli_runner.invoke(app, ["vm", "--help"])

        assert result.exit_code == 0
        assert "list" in result.stdout
        assert "get" in result.stdout
        assert "create" in result.stdout
        assert "start" in result.stdout
        assert "stop" in result.stdout


class TestNetworkCommands:
    """Tests for network commands."""

    def test_network_help(self, cli_runner: CliRunner) -> None:
        """Test network --help."""
        result = cli_runner.invoke(app, ["network", "--help"])

        assert result.exit_code == 0
        assert "list" in result.stdout
        assert "get" in result.stdout
        assert "create" in result.stdout
        assert "start" in result.stdout
        assert "stop" in result.stdout


class TestOutputFlag:
    """Tests for --output flag validation."""

    def test_output_flag_accepts_valid_formats(self, cli_runner, mock_client):
        """Test that --output accepts table, wide, json, csv."""
        for fmt in ["table", "wide", "json", "csv"]:
            result = cli_runner.invoke(app, ["--output", fmt, "system", "info"])
            assert result.exit_code != 2, f"--output {fmt} rejected: {result.output}"

    def test_output_flag_rejects_invalid_format(self, cli_runner):
        """Test that --output rejects invalid formats."""
        result = cli_runner.invoke(app, ["--output", "yaml", "system", "info"])
        assert result.exit_code == 2
        assert "'yaml' is not one of" in result.output
        assert "Traceback" not in result.output

    def test_explicit_table_overrides_json_config(self, cli_runner, mock_client):
        """An explicit --output table should override the configured default."""
        with patch("verge_cli.cli.get_effective_config", return_value=ProfileConfig(output="json")):
            result = cli_runner.invoke(app, ["--output", "table", "system", "info"])

        assert result.exit_code == 0
        assert "Field" in result.output

    def test_invalid_env_output_is_config_error(self, cli_runner, monkeypatch):
        """Invalid VERGE_OUTPUT should fail cleanly instead of falling through."""
        monkeypatch.setenv("VERGE_OUTPUT", "yaml")

        result = cli_runner.invoke(app, ["system", "info"])

        assert result.exit_code == 3
        assert "Invalid output format 'yaml'" in result.output
        assert "Traceback" not in result.output


class TestSystemCommands:
    """Tests for system commands."""

    def test_system_help(self, cli_runner: CliRunner) -> None:
        """Test system --help."""
        result = cli_runner.invoke(app, ["system", "--help"])

        assert result.exit_code == 0
        assert "info" in result.stdout
        assert "version" in result.stdout


class TestTenantCommands:
    """Tests for tenant commands."""

    def test_tenant_help(self, cli_runner: CliRunner) -> None:
        """Test tenant --help."""
        result = cli_runner.invoke(app, ["tenant", "--help"])

        assert result.exit_code == 0
        assert "list" in result.stdout
        assert "get" in result.stdout
        assert "create" in result.stdout
        assert "update" in result.stdout
        assert "delete" in result.stdout
        assert "start" in result.stdout
        assert "stop" in result.stdout
        assert "restart" in result.stdout
        assert "reset" in result.stdout
        assert "clone" in result.stdout
        assert "isolate" in result.stdout
        assert "crash-cart" in result.stdout
        assert "send-file" in result.stdout
