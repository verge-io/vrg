"""Tests for network query commands."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from pyvergeos.exceptions import VergeTimeoutError

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
    result.key = "abc123def456"
    return result


@pytest.fixture
def mock_network_for_query():
    """Create a mock Network with queries manager."""
    net = MagicMock()
    net.key = 1
    net.name = "test-network"

    def mock_get(key: str, default=None):
        return {"running": True}.get(key, default)

    net.get = mock_get
    return net


def test_ping(cli_runner, mock_client, mock_network_for_query, mock_query_result):
    """Ping should call queries.run with correct args."""
    mock_client.networks.list.return_value = [mock_network_for_query]
    mock_client.networks.get.return_value = mock_network_for_query
    mock_network_for_query.queries.run.return_value = mock_query_result

    result = cli_runner.invoke(app, ["network", "query", "ping", "test-network", "8.8.8.8"])

    assert result.exit_code == 0
    mock_network_for_query.queries.run.assert_called_once_with(
        "ping", {"host": "8.8.8.8"}, timeout=30,
    )
    assert "8.8.8.8" in result.output


def test_ping_custom_timeout(cli_runner, mock_client, mock_network_for_query, mock_query_result):
    """--timeout should be forwarded to SDK."""
    mock_client.networks.list.return_value = [mock_network_for_query]
    mock_client.networks.get.return_value = mock_network_for_query
    mock_network_for_query.queries.run.return_value = mock_query_result

    result = cli_runner.invoke(
        app, ["network", "query", "ping", "test-network", "8.8.8.8", "--timeout", "10"]
    )

    assert result.exit_code == 0
    mock_network_for_query.queries.run.assert_called_once_with(
        "ping", {"host": "8.8.8.8"}, timeout=10.0,
    )


def test_dns(cli_runner, mock_client, mock_network_for_query, mock_query_result):
    """DNS should call queries.run with name param."""
    mock_client.networks.list.return_value = [mock_network_for_query]
    mock_client.networks.get.return_value = mock_network_for_query
    mock_query_result.query_type = "dns"
    mock_query_result.result = "example.com has address 93.184.216.34"
    mock_network_for_query.queries.run.return_value = mock_query_result

    result = cli_runner.invoke(app, ["network", "query", "dns", "test-network", "example.com"])

    assert result.exit_code == 0
    mock_network_for_query.queries.run.assert_called_once_with(
        "dns", {"name": "example.com"}, timeout=30,
    )
    assert "93.184.216.34" in result.output


def test_traceroute(cli_runner, mock_client, mock_network_for_query, mock_query_result):
    """Traceroute should call queries.run with host param."""
    mock_client.networks.list.return_value = [mock_network_for_query]
    mock_client.networks.get.return_value = mock_network_for_query
    mock_query_result.query_type = "traceroute"
    mock_query_result.result = " 1  10.0.0.1  1.234 ms"
    mock_network_for_query.queries.run.return_value = mock_query_result

    result = cli_runner.invoke(
        app, ["network", "query", "traceroute", "test-network", "8.8.8.8"]
    )

    assert result.exit_code == 0
    mock_network_for_query.queries.run.assert_called_once_with(
        "traceroute", {"host": "8.8.8.8"}, timeout=60,
    )
    assert "10.0.0.1" in result.output


def test_tcpdump_defaults(cli_runner, mock_client, mock_network_for_query, mock_query_result):
    """Tcpdump with no options should call run with no params."""
    mock_client.networks.list.return_value = [mock_network_for_query]
    mock_client.networks.get.return_value = mock_network_for_query
    mock_query_result.query_type = "tcpdump"
    mock_query_result.result = "12:00:00.000000 IP 10.0.0.1 > 10.0.0.2: ICMP echo request"
    mock_network_for_query.queries.run.return_value = mock_query_result

    result = cli_runner.invoke(app, ["network", "query", "tcpdump", "test-network"])

    assert result.exit_code == 0
    mock_network_for_query.queries.run.assert_called_once_with(
        "tcpdump", None, timeout=120,
    )


def test_tcpdump_with_options(cli_runner, mock_client, mock_network_for_query, mock_query_result):
    """Tcpdump --interface, --count, --filter should be forwarded as params."""
    mock_client.networks.list.return_value = [mock_network_for_query]
    mock_client.networks.get.return_value = mock_network_for_query
    mock_query_result.query_type = "tcpdump"
    mock_query_result.result = "captured packets"
    mock_network_for_query.queries.run.return_value = mock_query_result

    result = cli_runner.invoke(
        app,
        [
            "network", "query", "tcpdump", "test-network",
            "--interface", "eth0",
            "--count", "10",
            "--filter", "icmp",
        ],
    )

    assert result.exit_code == 0
    mock_network_for_query.queries.run.assert_called_once_with(
        "tcpdump",
        {"interface": "eth0", "count": 10, "filter": "icmp"},
        timeout=120,
    )


def test_network_not_found(cli_runner, mock_client):
    """Bad network name should exit with code 6 (NOT_FOUND)."""
    mock_client.networks.list.return_value = []

    result = cli_runner.invoke(app, ["network", "query", "ping", "nonexistent", "8.8.8.8"])

    assert result.exit_code == 6


def test_json_output(cli_runner, mock_client, mock_network_for_query, mock_query_result):
    """-o json should produce valid JSON dict."""
    import json

    mock_client.networks.list.return_value = [mock_network_for_query]
    mock_client.networks.get.return_value = mock_network_for_query
    mock_network_for_query.queries.run.return_value = mock_query_result

    result = cli_runner.invoke(
        app, ["-o", "json", "network", "query", "ping", "test-network", "8.8.8.8"]
    )

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["query_type"] == "ping"
    assert data["status"] == "complete"
    assert data["key"] == "abc123def456"


def test_timeout_error(cli_runner, mock_client, mock_network_for_query):
    """VergeTimeoutError should exit with code 9."""
    mock_client.networks.list.return_value = [mock_network_for_query]
    mock_client.networks.get.return_value = mock_network_for_query
    mock_network_for_query.queries.run.side_effect = VergeTimeoutError("timed out")

    result = cli_runner.invoke(app, ["network", "query", "ping", "test-network", "8.8.8.8"])

    assert result.exit_code == 9
