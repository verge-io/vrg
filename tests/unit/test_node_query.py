"""Tests for node query commands."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from verge_cli.cli import app


@pytest.fixture
def mock_query_result():
    """Create a mock QueryResult."""
    result = MagicMock()
    result.result = "PING 8.8.8.8 (8.8.8.8) 56 data bytes\n64 bytes from 8.8.8.8: icmp_seq=1 ttl=118"
    result.status = "complete"
    result.is_error = False
    result.is_complete = True
    result.query_type = "ping"
    result.command = "ping -c 4 8.8.8.8"
    result.key = "node123def456"
    return result


@pytest.fixture
def mock_node_for_query():
    """Create a mock Node with queries manager."""
    node = MagicMock()
    node.key = 1
    node.name = "node1"

    def mock_get(key: str, default=None):
        return {"status": "online"}.get(key, default)

    node.get = mock_get
    return node


def test_ping(cli_runner, mock_client, mock_node_for_query, mock_query_result):
    """Ping should call queries.run with correct args."""
    mock_client.nodes.list.return_value = [mock_node_for_query]
    mock_client.nodes.get.return_value = mock_node_for_query
    mock_node_for_query.queries.run.return_value = mock_query_result

    result = cli_runner.invoke(app, ["node", "query", "ping", "node1", "8.8.8.8"])

    assert result.exit_code == 0
    mock_node_for_query.queries.run.assert_called_once_with(
        "ping", {"host": "8.8.8.8"}, timeout=30,
    )


def test_dns(cli_runner, mock_client, mock_node_for_query, mock_query_result):
    """DNS should call queries.run with name param."""
    mock_client.nodes.list.return_value = [mock_node_for_query]
    mock_client.nodes.get.return_value = mock_node_for_query
    mock_query_result.query_type = "dns"
    mock_query_result.result = "example.com has address 93.184.216.34"
    mock_node_for_query.queries.run.return_value = mock_query_result

    result = cli_runner.invoke(app, ["node", "query", "dns", "node1", "example.com"])

    assert result.exit_code == 0
    mock_node_for_query.queries.run.assert_called_once_with(
        "dns", {"name": "example.com"}, timeout=30,
    )


def test_traceroute(cli_runner, mock_client, mock_node_for_query, mock_query_result):
    """Traceroute should call queries.run with host param."""
    mock_client.nodes.list.return_value = [mock_node_for_query]
    mock_client.nodes.get.return_value = mock_node_for_query
    mock_query_result.query_type = "traceroute"
    mock_query_result.result = " 1  10.0.0.1  1.234 ms"
    mock_node_for_query.queries.run.return_value = mock_query_result

    result = cli_runner.invoke(app, ["node", "query", "traceroute", "node1", "8.8.8.8"])

    assert result.exit_code == 0
    mock_node_for_query.queries.run.assert_called_once_with(
        "traceroute", {"host": "8.8.8.8"}, timeout=60,
    )


def test_tcpdump_defaults(cli_runner, mock_client, mock_node_for_query, mock_query_result):
    """Tcpdump with no options should call run with no params."""
    mock_client.nodes.list.return_value = [mock_node_for_query]
    mock_client.nodes.get.return_value = mock_node_for_query
    mock_query_result.query_type = "tcpdump"
    mock_query_result.result = "captured packets"
    mock_node_for_query.queries.run.return_value = mock_query_result

    result = cli_runner.invoke(app, ["node", "query", "tcpdump", "node1"])

    assert result.exit_code == 0
    mock_node_for_query.queries.run.assert_called_once_with("tcpdump", None, timeout=120)


def test_tcpdump_with_options(cli_runner, mock_client, mock_node_for_query, mock_query_result):
    """Tcpdump options should be forwarded as params."""
    mock_client.nodes.list.return_value = [mock_node_for_query]
    mock_client.nodes.get.return_value = mock_node_for_query
    mock_query_result.query_type = "tcpdump"
    mock_query_result.result = "captured packets"
    mock_node_for_query.queries.run.return_value = mock_query_result

    result = cli_runner.invoke(
        app,
        ["node", "query", "tcpdump", "node1", "--interface", "eth0", "--count", "5"],
    )

    assert result.exit_code == 0
    mock_node_for_query.queries.run.assert_called_once_with(
        "tcpdump", {"interface": "eth0", "count": 5}, timeout=120,
    )


def test_arp(cli_runner, mock_client, mock_node_for_query, mock_query_result):
    """ARP should call queries.run with arp type."""
    mock_client.nodes.list.return_value = [mock_node_for_query]
    mock_client.nodes.get.return_value = mock_node_for_query
    mock_query_result.query_type = "arp"
    mock_query_result.result = "? (10.0.0.1) at 00:50:56:00:00:01 [ether] on eth0"
    mock_node_for_query.queries.run.return_value = mock_query_result

    result = cli_runner.invoke(app, ["node", "query", "arp", "node1"])

    assert result.exit_code == 0
    mock_node_for_query.queries.run.assert_called_once_with("arp", None, timeout=30)


def test_arp_scan(cli_runner, mock_client, mock_node_for_query, mock_query_result):
    """ARP scan should call queries.run with arp-scan type."""
    mock_client.nodes.list.return_value = [mock_node_for_query]
    mock_client.nodes.get.return_value = mock_node_for_query
    mock_query_result.query_type = "arp-scan"
    mock_query_result.result = "10.0.0.1\t00:50:56:00:00:01"
    mock_node_for_query.queries.run.return_value = mock_query_result

    result = cli_runner.invoke(app, ["node", "query", "arp-scan", "node1"])

    assert result.exit_code == 0
    mock_node_for_query.queries.run.assert_called_once_with("arp-scan", None, timeout=30)


def test_node_not_found(cli_runner, mock_client):
    """Bad node name should exit with code 6 (NOT_FOUND)."""
    mock_client.nodes.list.return_value = []

    result = cli_runner.invoke(app, ["node", "query", "ping", "nonexistent", "8.8.8.8"])

    assert result.exit_code == 6


def test_json_output(cli_runner, mock_client, mock_node_for_query, mock_query_result):
    """-o json should produce valid JSON dict."""
    mock_client.nodes.list.return_value = [mock_node_for_query]
    mock_client.nodes.get.return_value = mock_node_for_query
    mock_node_for_query.queries.run.return_value = mock_query_result

    result = cli_runner.invoke(
        app, ["-o", "json", "node", "query", "ping", "node1", "8.8.8.8"]
    )

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["query_type"] == "ping"
    assert data["status"] == "complete"
    assert data["key"] == "node123def456"
