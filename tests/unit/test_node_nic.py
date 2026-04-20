"""Tests for node NIC monitoring commands."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest
from pyvergeos.exceptions import NotFoundError

from verge_cli.cli import app


@pytest.fixture
def mock_node_for_nic():
    """Create a mock Node with NIC manager."""
    node = MagicMock()
    node.key = 1
    node.name = "node1"

    def mock_get(key: str, default=None):
        return {"status": "online"}.get(key, default)

    node.get = mock_get
    return node


class DictLike(dict):
    """Dict subclass that mimics SDK ResourceObject for testing."""

    pass


@pytest.fixture
def mock_nic():
    """Create a mock NIC with stats/status/fabric managers."""
    nic = MagicMock()
    nic.key = 13
    nic.get.return_value = None

    # Stats
    stats = DictLike(
        {
            "$key": 13,
            "parent_nic": 13,
            "txpps": 320,
            "rxpps": 204,
            "txbps": 2287335,
            "rxbps": 916639,
            "totalxbps": 3203974,
            "tx_pckts": 100000,
            "rx_pckts": 80000,
            "tx_bytes": 500000000,
            "rx_bytes": 400000000,
        }
    )
    nic.nic_stats.get.return_value = stats

    # Status
    status = DictLike(
        {
            "$key": 13,
            "parent_nic": 13,
            "status": "up",
            "state": "online",
            "speed": 25000,
            "last_update": 1774203406,
        }
    )
    nic.link_status.get.return_value = status

    # Fabric
    fabric = DictLike(
        {
            "$key": 13,
            "parent_nic": 13,
            "status": "confirmed",
            "state": "online",
            "max_score": 50,
            "min_score": 50,
        }
    )
    nic.fabric_status.get.return_value = fabric

    return nic


def test_nic_stats_all(cli_runner, mock_client, mock_node_for_nic, mock_nic):
    """Shows stats for all NICs on a node."""
    mock_client.nodes.list.return_value = [mock_node_for_nic]
    mock_client.nodes.get.return_value = mock_node_for_nic
    mock_node_for_nic.nics.list.return_value = [mock_nic]

    result = cli_runner.invoke(app, ["node", "nic", "stats", "node1"])

    assert result.exit_code == 0
    assert "13" in result.output
    assert "320" in result.output


def test_nic_stats_single(cli_runner, mock_client, mock_node_for_nic, mock_nic):
    """--nic flag shows single NIC stats."""
    mock_client.nodes.list.return_value = [mock_node_for_nic]
    mock_client.nodes.get.return_value = mock_node_for_nic
    mock_node_for_nic.nics.get.return_value = mock_nic

    result = cli_runner.invoke(app, ["node", "nic", "stats", "node1", "--nic", "13"])

    assert result.exit_code == 0
    mock_node_for_nic.nics.get.assert_called_once_with(key=13)


def test_nic_stats_json(cli_runner, mock_client, mock_node_for_nic, mock_nic):
    """JSON output includes all stat fields."""
    mock_client.nodes.list.return_value = [mock_node_for_nic]
    mock_client.nodes.get.return_value = mock_node_for_nic
    mock_node_for_nic.nics.list.return_value = [mock_nic]

    result = cli_runner.invoke(app, ["-o", "json", "node", "nic", "stats", "node1"])

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data) == 1
    assert data[0]["txpps"] == 320
    assert data[0]["totalxbps"] == 3203974


def test_nic_status_all(cli_runner, mock_client, mock_node_for_nic, mock_nic):
    """Shows link status for all NICs."""
    mock_client.nodes.list.return_value = [mock_node_for_nic]
    mock_client.nodes.get.return_value = mock_node_for_nic
    mock_node_for_nic.nics.list.return_value = [mock_nic]

    result = cli_runner.invoke(app, ["node", "nic", "status", "node1"])

    assert result.exit_code == 0
    assert "up" in result.output
    assert "online" in result.output


def test_nic_status_single(cli_runner, mock_client, mock_node_for_nic, mock_nic):
    """--nic flag works for status."""
    mock_client.nodes.list.return_value = [mock_node_for_nic]
    mock_client.nodes.get.return_value = mock_node_for_nic
    mock_node_for_nic.nics.get.return_value = mock_nic

    result = cli_runner.invoke(app, ["node", "nic", "status", "node1", "--nic", "13"])

    assert result.exit_code == 0
    mock_node_for_nic.nics.get.assert_called_once_with(key=13)


def test_nic_fabric_all(cli_runner, mock_client, mock_node_for_nic, mock_nic):
    """Shows fabric status for all NICs."""
    mock_client.nodes.list.return_value = [mock_node_for_nic]
    mock_client.nodes.get.return_value = mock_node_for_nic
    mock_node_for_nic.nics.list.return_value = [mock_nic]

    result = cli_runner.invoke(app, ["node", "nic", "fabric", "node1"])

    assert result.exit_code == 0
    assert "confirmed" in result.output


def test_nic_fabric_single(cli_runner, mock_client, mock_node_for_nic, mock_nic):
    """--nic flag works for fabric."""
    mock_client.nodes.list.return_value = [mock_node_for_nic]
    mock_client.nodes.get.return_value = mock_node_for_nic
    mock_node_for_nic.nics.get.return_value = mock_nic

    result = cli_runner.invoke(app, ["node", "nic", "fabric", "node1", "--nic", "13"])

    assert result.exit_code == 0
    mock_node_for_nic.nics.get.assert_called_once_with(key=13)


def test_nic_fabric_skips_missing(cli_runner, mock_client, mock_node_for_nic):
    """NICs without fabric records are skipped gracefully."""
    mock_client.nodes.list.return_value = [mock_node_for_nic]
    mock_client.nodes.get.return_value = mock_node_for_nic

    nic_down = MagicMock()
    nic_down.key = 7
    nic_down.fabric_status.get.side_effect = NotFoundError("not found")

    mock_node_for_nic.nics.list.return_value = [nic_down]

    result = cli_runner.invoke(app, ["node", "nic", "fabric", "node1"])

    assert result.exit_code == 0
    assert "No results" in result.output


def test_nic_node_not_found(cli_runner, mock_client):
    """Bad node → exit code 6."""
    mock_client.nodes.list.return_value = []

    result = cli_runner.invoke(app, ["node", "nic", "stats", "nonexistent"])

    assert result.exit_code == 6
