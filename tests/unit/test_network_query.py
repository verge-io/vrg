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
    result.result = (
        "PING 8.8.8.8 (8.8.8.8) 56 data bytes\n64 bytes from 8.8.8.8: icmp_seq=1 ttl=118"
    )
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
        "ping",
        {"host": "8.8.8.8"},
        timeout=30,
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
        "ping",
        {"host": "8.8.8.8"},
        timeout=10.0,
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
        "dns",
        {"name": "example.com"},
        timeout=30,
    )
    assert "93.184.216.34" in result.output


def test_traceroute(cli_runner, mock_client, mock_network_for_query, mock_query_result):
    """Traceroute should call queries.run with host param."""
    mock_client.networks.list.return_value = [mock_network_for_query]
    mock_client.networks.get.return_value = mock_network_for_query
    mock_query_result.query_type = "traceroute"
    mock_query_result.result = " 1  10.0.0.1  1.234 ms"
    mock_network_for_query.queries.run.return_value = mock_query_result

    result = cli_runner.invoke(app, ["network", "query", "traceroute", "test-network", "8.8.8.8"])

    assert result.exit_code == 0
    mock_network_for_query.queries.run.assert_called_once_with(
        "traceroute",
        {"host": "8.8.8.8"},
        timeout=60,
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
        "tcpdump",
        None,
        timeout=120,
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
            "network",
            "query",
            "tcpdump",
            "test-network",
            "--interface",
            "eth0",
            "--count",
            "10",
            "--filter",
            "icmp",
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


def test_arp(cli_runner, mock_client, mock_network_for_query, mock_query_result):
    """ARP should call queries.run with arp type."""
    mock_client.networks.list.return_value = [mock_network_for_query]
    mock_client.networks.get.return_value = mock_network_for_query
    mock_query_result.query_type = "arp"
    mock_query_result.result = "? (10.0.0.1) at 00:50:56:00:00:01 [ether] on eth0"
    mock_network_for_query.queries.run.return_value = mock_query_result

    result = cli_runner.invoke(app, ["network", "query", "arp", "test-network"])

    assert result.exit_code == 0
    mock_network_for_query.queries.run.assert_called_once_with("arp", None, timeout=30)


def test_arp_scan(cli_runner, mock_client, mock_network_for_query, mock_query_result):
    """ARP scan should call queries.run with arp-scan type."""
    mock_client.networks.list.return_value = [mock_network_for_query]
    mock_client.networks.get.return_value = mock_network_for_query
    mock_query_result.query_type = "arp-scan"
    mock_query_result.result = "10.0.0.1\t00:50:56:00:00:01"
    mock_network_for_query.queries.run.return_value = mock_query_result

    result = cli_runner.invoke(app, ["network", "query", "arp-scan", "test-network"])

    assert result.exit_code == 0
    mock_network_for_query.queries.run.assert_called_once_with("arp-scan", None, timeout=30)


def test_firewall(cli_runner, mock_client, mock_network_for_query, mock_query_result):
    """Firewall should call queries.run with firewall type."""
    mock_client.networks.list.return_value = [mock_network_for_query]
    mock_client.networks.get.return_value = mock_network_for_query
    mock_query_result.query_type = "firewall"
    mock_query_result.result = "table inet filter {\n  chain input {\n  }\n}"
    mock_network_for_query.queries.run.return_value = mock_query_result

    result = cli_runner.invoke(app, ["network", "query", "firewall", "test-network"])

    assert result.exit_code == 0
    mock_network_for_query.queries.run.assert_called_once_with("firewall", None, timeout=30)


def test_trace(cli_runner, mock_client, mock_network_for_query, mock_query_result):
    """Trace should call queries.run with trace type."""
    mock_client.networks.list.return_value = [mock_network_for_query]
    mock_client.networks.get.return_value = mock_network_for_query
    mock_query_result.query_type = "trace"
    mock_query_result.result = "trace id 1 inet filter input"
    mock_network_for_query.queries.run.return_value = mock_query_result

    result = cli_runner.invoke(app, ["network", "query", "trace", "test-network"])

    assert result.exit_code == 0
    mock_network_for_query.queries.run.assert_called_once_with("trace", None, timeout=30)


def test_nmap(cli_runner, mock_client, mock_network_for_query, mock_query_result):
    """Nmap should call queries.run with host param."""
    mock_client.networks.list.return_value = [mock_network_for_query]
    mock_client.networks.get.return_value = mock_network_for_query
    mock_query_result.query_type = "nmap"
    mock_query_result.result = "Host: 10.0.0.1 () Ports: 22/open/tcp//ssh///"
    mock_network_for_query.queries.run.return_value = mock_query_result

    result = cli_runner.invoke(app, ["network", "query", "nmap", "test-network", "10.0.0.0/24"])

    assert result.exit_code == 0
    mock_network_for_query.queries.run.assert_called_once_with(
        "nmap",
        {"host": "10.0.0.0/24"},
        timeout=120,
    )


def test_tcp_connect(cli_runner, mock_client, mock_network_for_query, mock_query_result):
    """TCP connect should call queries.run with host and port params."""
    mock_client.networks.list.return_value = [mock_network_for_query]
    mock_client.networks.get.return_value = mock_network_for_query
    mock_query_result.query_type = "tcp_connect"
    mock_query_result.result = "Connected to 10.0.0.1:443"
    mock_network_for_query.queries.run.return_value = mock_query_result

    result = cli_runner.invoke(
        app, ["network", "query", "tcp-connect", "test-network", "10.0.0.1", "443"]
    )

    assert result.exit_code == 0
    mock_network_for_query.queries.run.assert_called_once_with(
        "tcp_connect",
        {"host": "10.0.0.1", "port": 443},
        timeout=30,
    )


def test_run_generic(cli_runner, mock_client, mock_network_for_query, mock_query_result):
    """Generic run with custom type + JSON params."""
    mock_client.networks.list.return_value = [mock_network_for_query]
    mock_client.networks.get.return_value = mock_network_for_query
    mock_query_result.query_type = "ip"
    mock_query_result.result = "1: lo: <LOOPBACK,UP>"
    mock_network_for_query.queries.run.return_value = mock_query_result

    result = cli_runner.invoke(
        app,
        ["network", "query", "run", "test-network", "ip", "--params", '{"cmd": "addr"}'],
    )

    assert result.exit_code == 0
    mock_network_for_query.queries.run.assert_called_once_with(
        "ip",
        {"cmd": "addr"},
        timeout=120,
    )


def test_run_generic_no_params(cli_runner, mock_client, mock_network_for_query, mock_query_result):
    """Generic run with type only, no --params."""
    mock_client.networks.list.return_value = [mock_network_for_query]
    mock_client.networks.get.return_value = mock_network_for_query
    mock_query_result.query_type = "whatsmyip"
    mock_query_result.result = "203.0.113.1"
    mock_network_for_query.queries.run.return_value = mock_query_result

    result = cli_runner.invoke(app, ["network", "query", "run", "test-network", "whatsmyip"])

    assert result.exit_code == 0
    mock_network_for_query.queries.run.assert_called_once_with(
        "whatsmyip",
        None,
        timeout=120,
    )
