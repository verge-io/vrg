"""Tests for node LLDP neighbor commands."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from verge_cli.cli import app


@pytest.fixture
def mock_node_for_lldp():
    """Create a mock Node with LLDP neighbors manager."""
    node = MagicMock()
    node.key = 1
    node.name = "node1"

    def mock_get(key: str, default=None):
        return {"status": "online"}.get(key, default)

    node.get = mock_get
    return node


@pytest.fixture
def mock_lldp_neighbor():
    """Create a mock LLDP neighbor."""
    n = MagicMock()
    n.key = 42
    n.nic_key = 5
    n.chassis_name = "switch-01.lab"
    n.port_id = "Ethernet1/1"
    n.via = "LLDP"
    n.age = "120s"
    n.remote_id = "aa:bb:cc:dd:ee:ff"
    return n


def test_lldp_list(cli_runner, mock_client, mock_node_for_lldp, mock_lldp_neighbor):
    """List LLDP neighbors for a node."""
    mock_client.nodes.list.return_value = [mock_node_for_lldp]
    mock_client.nodes.get.return_value = mock_node_for_lldp
    mock_node_for_lldp.lldp_neighbors.list.return_value = [mock_lldp_neighbor]

    result = cli_runner.invoke(app, ["node", "lldp", "list", "node1"])

    assert result.exit_code == 0
    assert "switch-01.lab" in result.output
    assert "Ethernet1/1" in result.output


def test_lldp_list_empty(cli_runner, mock_client, mock_node_for_lldp):
    """Handle no neighbors gracefully."""
    mock_client.nodes.list.return_value = [mock_node_for_lldp]
    mock_client.nodes.get.return_value = mock_node_for_lldp
    mock_node_for_lldp.lldp_neighbors.list.return_value = []

    result = cli_runner.invoke(app, ["node", "lldp", "list", "node1"])

    assert result.exit_code == 0
    assert "No results" in result.output


def test_lldp_list_by_nic(cli_runner, mock_client, mock_node_for_lldp, mock_lldp_neighbor):
    """--nic flag filters by NIC key."""
    mock_client.nodes.list.return_value = [mock_node_for_lldp]
    mock_client.nodes.get.return_value = mock_node_for_lldp
    mock_node_for_lldp.lldp_neighbors.list.return_value = [mock_lldp_neighbor]

    result = cli_runner.invoke(app, ["node", "lldp", "list", "node1", "--nic", "5"])

    assert result.exit_code == 0
    mock_node_for_lldp.lldp_neighbors.list.assert_called_once_with(filter="nic eq 5")


def test_lldp_list_json(cli_runner, mock_client, mock_node_for_lldp, mock_lldp_neighbor):
    """JSON output includes chassis/port details."""
    mock_client.nodes.list.return_value = [mock_node_for_lldp]
    mock_client.nodes.get.return_value = mock_node_for_lldp
    mock_node_for_lldp.lldp_neighbors.list.return_value = [mock_lldp_neighbor]

    result = cli_runner.invoke(app, ["-o", "json", "node", "lldp", "list", "node1"])

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data) == 1
    assert data[0]["chassis_name"] == "switch-01.lab"
    assert data[0]["port_id"] == "Ethernet1/1"


def test_lldp_node_not_found(cli_runner, mock_client):
    """Bad node name should exit with code 6."""
    mock_client.nodes.list.return_value = []

    result = cli_runner.invoke(app, ["node", "lldp", "list", "nonexistent"])

    assert result.exit_code == 6
