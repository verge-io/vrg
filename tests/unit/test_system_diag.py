"""Tests for system diagnostic commands."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from verge_cli.cli import app


@pytest.fixture
def mock_diag():
    """Create a mock SystemDiagnostic."""
    diag = MagicMock()
    diag.key = 1
    diag.name = "test-diag"
    diag.description = "Test diagnostic"
    diag.status = "complete"
    diag.is_complete = True
    diag.is_error = False
    diag.is_building = False
    diag.status_info = None
    diag.timestamp = 1713300000

    def mock_get(key: str, default=None):
        data = {
            "name": "test-diag",
            "description": "Test diagnostic",
            "status": "complete",
            "status_info": None,
            "timestamp": 1713300000,
        }
        return data.get(key, default)

    diag.get = mock_get
    return diag


def test_diag_list(cli_runner, mock_client, mock_diag):
    """List diagnostic bundles."""
    mock_client.system_diagnostics.list.return_value = [mock_diag]

    result = cli_runner.invoke(app, ["system", "diag", "list"])

    assert result.exit_code == 0
    assert "test-diag" in result.output


def test_diag_list_empty(cli_runner, mock_client):
    """Handle no diagnostics."""
    mock_client.system_diagnostics.list.return_value = []

    result = cli_runner.invoke(app, ["system", "diag", "list"])

    assert result.exit_code == 0
    assert "No results" in result.output


def test_diag_create_no_wait(cli_runner, mock_client, mock_diag):
    """--no-wait returns immediately."""
    mock_diag.status = "initializing"
    mock_client.system_diagnostics.create.return_value = mock_diag

    result = cli_runner.invoke(
        app, ["system", "diag", "create", "test-diag", "--no-wait"]
    )

    assert result.exit_code == 0
    mock_client.system_diagnostics.create.assert_called_once_with(
        name="test-diag", description="", send2support=False,
    )


def test_diag_create_send_to_support(cli_runner, mock_client, mock_diag):
    """--send-to-support flag is forwarded."""
    mock_diag.status = "initializing"
    mock_client.system_diagnostics.create.return_value = mock_diag

    result = cli_runner.invoke(
        app, ["system", "diag", "create", "test-diag", "--send-to-support", "--no-wait"]
    )

    assert result.exit_code == 0
    mock_client.system_diagnostics.create.assert_called_once_with(
        name="test-diag", description="", send2support=True,
    )


def test_diag_get_by_key(cli_runner, mock_client, mock_diag):
    """Resolve by numeric key."""
    mock_client.system_diagnostics.get.return_value = mock_diag

    result = cli_runner.invoke(app, ["system", "diag", "get", "1"])

    assert result.exit_code == 0
    mock_client.system_diagnostics.get.assert_called_once_with(key=1)
    assert "test-diag" in result.output


def test_diag_get_by_name(cli_runner, mock_client, mock_diag):
    """Resolve by name."""
    mock_client.system_diagnostics.get.return_value = mock_diag

    result = cli_runner.invoke(app, ["system", "diag", "get", "test-diag"])

    assert result.exit_code == 0
    mock_client.system_diagnostics.get.assert_called_once_with(name="test-diag")


def test_diag_send(cli_runner, mock_client, mock_diag):
    """Send calls send_to_support."""
    mock_client.system_diagnostics.get.return_value = mock_diag

    result = cli_runner.invoke(app, ["system", "diag", "send", "1"])

    assert result.exit_code == 0
    mock_client.system_diagnostics.send_to_support.assert_called_once_with(1)


def test_diag_delete_with_yes(cli_runner, mock_client, mock_diag):
    """Delete with --yes skips confirmation."""
    mock_client.system_diagnostics.get.return_value = mock_diag

    result = cli_runner.invoke(app, ["system", "diag", "delete", "1", "--yes"])

    assert result.exit_code == 0
    mock_client.system_diagnostics.delete.assert_called_once_with(1)


def test_diag_json(cli_runner, mock_client, mock_diag):
    """JSON output includes all fields."""
    mock_client.system_diagnostics.get.return_value = mock_diag

    result = cli_runner.invoke(app, ["-o", "json", "system", "diag", "get", "1"])

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["name"] == "test-diag"
    assert data["status"] == "complete"
    assert data["$key"] == 1
