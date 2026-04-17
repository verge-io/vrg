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


def test_smartctl(cli_runner, mock_client, mock_node_for_query, mock_query_result):
    """Smartctl should call queries.run with device param."""
    mock_client.nodes.list.return_value = [mock_node_for_query]
    mock_client.nodes.get.return_value = mock_node_for_query
    mock_query_result.query_type = "smartctl"
    mock_query_result.result = "SMART overall-health self-assessment test result: PASSED"
    mock_node_for_query.queries.run.return_value = mock_query_result

    result = cli_runner.invoke(
        app, ["node", "query", "smartctl", "node1", "/dev/sda"]
    )

    assert result.exit_code == 0
    mock_node_for_query.queries.run.assert_called_once_with(
        "smartctl", {"path": "/dev/sda"}, timeout=60,
    )
    assert "PASSED" in result.output


def test_smartctl_test(cli_runner, mock_client, mock_node_for_query, mock_query_result):
    """Smartctl-test should call queries.run with smartctl-test type."""
    mock_client.nodes.list.return_value = [mock_node_for_query]
    mock_client.nodes.get.return_value = mock_node_for_query
    mock_query_result.query_type = "smartctl-test"
    mock_query_result.result = "Self-test execution started"
    mock_node_for_query.queries.run.return_value = mock_query_result

    result = cli_runner.invoke(
        app, ["node", "query", "smartctl-test", "node1", "/dev/sda"]
    )

    assert result.exit_code == 0
    mock_node_for_query.queries.run.assert_called_once_with(
        "smartctl-test", {"path": "/dev/sda"}, timeout=60,
    )


def test_lsblk(cli_runner, mock_client, mock_node_for_query, mock_query_result):
    """Lsblk should call queries.run with lsblk type."""
    mock_client.nodes.list.return_value = [mock_node_for_query]
    mock_client.nodes.get.return_value = mock_node_for_query
    mock_query_result.query_type = "lsblk"
    mock_query_result.result = "NAME MAJ:MIN RM SIZE RO TYPE MOUNTPOINT\nsda 8:0 0 500G 0 disk"
    mock_node_for_query.queries.run.return_value = mock_query_result

    result = cli_runner.invoke(app, ["node", "query", "lsblk", "node1"])

    assert result.exit_code == 0
    mock_node_for_query.queries.run.assert_called_once_with("lsblk", None, timeout=30)
    assert "sda" in result.output


def test_dmidecode(cli_runner, mock_client, mock_node_for_query, mock_query_result):
    """Dmidecode should call queries.run with dmidecode type."""
    mock_client.nodes.list.return_value = [mock_node_for_query]
    mock_client.nodes.get.return_value = mock_node_for_query
    mock_query_result.query_type = "dmidecode"
    mock_query_result.result = "System Information\n  Manufacturer: Dell Inc."
    mock_node_for_query.queries.run.return_value = mock_query_result

    result = cli_runner.invoke(app, ["node", "query", "dmidecode", "node1"])

    assert result.exit_code == 0
    mock_node_for_query.queries.run.assert_called_once_with("dmidecode", None, timeout=30)
    assert "Dell" in result.output


def test_ipmi_sensor(cli_runner, mock_client, mock_node_for_query, mock_query_result):
    """IPMI sensor should call queries.run with ipmi-sensor type."""
    mock_client.nodes.list.return_value = [mock_node_for_query]
    mock_client.nodes.get.return_value = mock_node_for_query
    mock_query_result.query_type = "ipmi-sensor"
    mock_query_result.result = "CPU Temp | 45 degrees C | ok"
    mock_node_for_query.queries.run.return_value = mock_query_result

    result = cli_runner.invoke(app, ["node", "query", "ipmi-sensor", "node1"])

    assert result.exit_code == 0
    mock_node_for_query.queries.run.assert_called_once_with("ipmi-sensor", None, timeout=30)


def test_ipmi_sel(cli_runner, mock_client, mock_node_for_query, mock_query_result):
    """IPMI SEL should call queries.run with ipmi-sel type."""
    mock_client.nodes.list.return_value = [mock_node_for_query]
    mock_client.nodes.get.return_value = mock_node_for_query
    mock_query_result.query_type = "ipmi-sel"
    mock_query_result.result = "SEL has no entries"
    mock_node_for_query.queries.run.return_value = mock_query_result

    result = cli_runner.invoke(app, ["node", "query", "ipmi-sel", "node1"])

    assert result.exit_code == 0
    mock_node_for_query.queries.run.assert_called_once_with("ipmi-sel", None, timeout=30)


def test_ipmi_fru(cli_runner, mock_client, mock_node_for_query, mock_query_result):
    """IPMI FRU should call queries.run with ipmi-fru type."""
    mock_client.nodes.list.return_value = [mock_node_for_query]
    mock_client.nodes.get.return_value = mock_node_for_query
    mock_query_result.query_type = "ipmi-fru"
    mock_query_result.result = "FRU Device Description : Builtin FRU Device"
    mock_node_for_query.queries.run.return_value = mock_query_result

    result = cli_runner.invoke(app, ["node", "query", "ipmi-fru", "node1"])

    assert result.exit_code == 0
    mock_node_for_query.queries.run.assert_called_once_with("ipmi-fru", None, timeout=30)


def test_ipmi_lan(cli_runner, mock_client, mock_node_for_query, mock_query_result):
    """IPMI LAN should call queries.run with ipmi-lan type."""
    mock_client.nodes.list.return_value = [mock_node_for_query]
    mock_client.nodes.get.return_value = mock_node_for_query
    mock_query_result.query_type = "ipmi-lan"
    mock_query_result.result = "IP Address : 192.168.1.100"
    mock_node_for_query.queries.run.return_value = mock_query_result

    result = cli_runner.invoke(app, ["node", "query", "ipmi-lan", "node1"])

    assert result.exit_code == 0
    mock_node_for_query.queries.run.assert_called_once_with("ipmi-lan", None, timeout=30)


def test_ipmi_chassis(cli_runner, mock_client, mock_node_for_query, mock_query_result):
    """IPMI chassis should call queries.run with ipmi-chassis type."""
    mock_client.nodes.list.return_value = [mock_node_for_query]
    mock_client.nodes.get.return_value = mock_node_for_query
    mock_query_result.query_type = "ipmi-chassis"
    mock_query_result.result = "System Power : on"
    mock_node_for_query.queries.run.return_value = mock_query_result

    result = cli_runner.invoke(app, ["node", "query", "ipmi-chassis", "node1"])

    assert result.exit_code == 0
    mock_node_for_query.queries.run.assert_called_once_with("ipmi-chassis", None, timeout=30)


def test_run_generic(cli_runner, mock_client, mock_node_for_query, mock_query_result):
    """Generic run with custom type + JSON params."""
    mock_client.nodes.list.return_value = [mock_node_for_query]
    mock_client.nodes.get.return_value = mock_node_for_query
    mock_query_result.query_type = "ip"
    mock_query_result.result = "1: lo: <LOOPBACK,UP>"
    mock_node_for_query.queries.run.return_value = mock_query_result

    result = cli_runner.invoke(
        app,
        ["node", "query", "run", "node1", "ip", "--params", '{"cmd": "addr"}'],
    )

    assert result.exit_code == 0
    mock_node_for_query.queries.run.assert_called_once_with(
        "ip", {"cmd": "addr"}, timeout=120,
    )


def test_run_generic_no_params(cli_runner, mock_client, mock_node_for_query, mock_query_result):
    """Generic run with type only, no --params."""
    mock_client.nodes.list.return_value = [mock_node_for_query]
    mock_client.nodes.get.return_value = mock_node_for_query
    mock_query_result.query_type = "whatsmyip"
    mock_query_result.result = "203.0.113.1"
    mock_node_for_query.queries.run.return_value = mock_query_result

    result = cli_runner.invoke(app, ["node", "query", "run", "node1", "whatsmyip"])

    assert result.exit_code == 0
    mock_node_for_query.queries.run.assert_called_once_with("whatsmyip", None, timeout=120)


def test_run_invalid_json(cli_runner, mock_client, mock_node_for_query):
    """Bad --params JSON should exit with a clear error."""
    mock_client.nodes.list.return_value = [mock_node_for_query]
    mock_client.nodes.get.return_value = mock_node_for_query

    result = cli_runner.invoke(
        app, ["node", "query", "run", "node1", "ip", "--params", "not-json"]
    )

    assert result.exit_code == 1
    assert "Invalid JSON" in result.output
