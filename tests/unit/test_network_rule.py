"""Tests for network firewall rule commands."""

from unittest.mock import MagicMock

import pytest

from verge_cli.cli import app


@pytest.fixture
def mock_network_for_rules():
    """Create a mock Network for rule operations."""
    net = MagicMock()
    net.key = 1
    net.name = "test-network"

    def mock_get(key: str, default=None):
        return {"running": True}.get(key, default)

    net.get = mock_get
    return net


@pytest.fixture
def mock_rule():
    """Create a mock NetworkRule object."""
    rule = MagicMock()
    rule.key = 100
    rule.name = "Allow-HTTPS"

    def mock_get(key: str, default=None):
        data = {
            "name": "Allow-HTTPS",
            "direction": "incoming",
            "action": "accept",
            "protocol": "tcp",
            "destination_ports": "443",
            "enabled": True,
            "orderid": 1,
            "system_rule": False,
            "statistics": True,
            "trace": False,
            "packets": 12345,
            "bytes": 6789012,
        }
        return data.get(key, default)

    rule.get = mock_get
    rule.is_system_rule = False
    rule.is_enabled = True
    return rule


def test_rule_list(cli_runner, mock_client, mock_network_for_rules, mock_rule):
    """Rule list should show rules for a network."""
    mock_client.networks.list.return_value = [mock_network_for_rules]
    mock_client.networks.get.return_value = mock_network_for_rules
    mock_network_for_rules.rules.list.return_value = [mock_rule]

    result = cli_runner.invoke(app, ["network", "rule", "list", "test-network"])

    assert result.exit_code == 0
    # Output may truncate columns in table format, check for partial match
    assert "Allow" in result.output
    assert "100" in result.output  # $key column
    assert "accept" in result.output


def test_rule_get(cli_runner, mock_client, mock_network_for_rules, mock_rule):
    """Rule get should show rule details."""
    mock_client.networks.list.return_value = [mock_network_for_rules]
    mock_client.networks.get.return_value = mock_network_for_rules
    mock_network_for_rules.rules.list.return_value = [mock_rule]
    mock_network_for_rules.rules.get.return_value = mock_rule

    result = cli_runner.invoke(app, ["network", "rule", "get", "test-network", "Allow-HTTPS"])

    assert result.exit_code == 0
    assert "Allow-HTTPS" in result.output


def test_rule_create(cli_runner, mock_client, mock_network_for_rules, mock_rule):
    """Rule create should create a new rule."""
    mock_client.networks.list.return_value = [mock_network_for_rules]
    mock_client.networks.get.return_value = mock_network_for_rules
    mock_network_for_rules.rules.create.return_value = mock_rule

    result = cli_runner.invoke(
        app,
        [
            "network",
            "rule",
            "create",
            "test-network",
            "--name",
            "Allow-HTTPS",
            "--direction",
            "incoming",
            "--action",
            "accept",
            "--protocol",
            "tcp",
            "--dest-ports",
            "443",
        ],
    )

    assert result.exit_code == 0
    mock_network_for_rules.rules.create.assert_called_once()


def test_rule_update(cli_runner, mock_client, mock_network_for_rules, mock_rule):
    """Rule update should update a rule."""
    mock_client.networks.list.return_value = [mock_network_for_rules]
    mock_client.networks.get.return_value = mock_network_for_rules
    mock_network_for_rules.rules.list.return_value = [mock_rule]
    mock_network_for_rules.rules.update.return_value = mock_rule

    result = cli_runner.invoke(
        app,
        ["network", "rule", "update", "test-network", "Allow-HTTPS", "--enabled"],
    )

    assert result.exit_code == 0
    mock_network_for_rules.rules.update.assert_called_once()


def test_rule_delete(cli_runner, mock_client, mock_network_for_rules, mock_rule):
    """Rule delete should delete a rule."""
    mock_client.networks.list.return_value = [mock_network_for_rules]
    mock_client.networks.get.return_value = mock_network_for_rules
    mock_network_for_rules.rules.list.return_value = [mock_rule]
    mock_network_for_rules.rules.get.return_value = mock_rule

    result = cli_runner.invoke(
        app,
        ["network", "rule", "delete", "test-network", "Allow-HTTPS", "--yes"],
    )

    assert result.exit_code == 0
    mock_network_for_rules.rules.delete.assert_called_once_with(100)


def test_rule_enable(cli_runner, mock_client, mock_network_for_rules, mock_rule):
    """Rule enable should enable a rule."""
    mock_client.networks.list.return_value = [mock_network_for_rules]
    mock_client.networks.get.return_value = mock_network_for_rules
    mock_network_for_rules.rules.list.return_value = [mock_rule]
    mock_network_for_rules.rules.get.return_value = mock_rule

    result = cli_runner.invoke(
        app,
        ["network", "rule", "enable", "test-network", "Allow-HTTPS"],
    )

    assert result.exit_code == 0
    mock_rule.enable.assert_called_once()


def test_rule_disable(cli_runner, mock_client, mock_network_for_rules, mock_rule):
    """Rule disable should disable a rule."""
    mock_client.networks.list.return_value = [mock_network_for_rules]
    mock_client.networks.get.return_value = mock_network_for_rules
    mock_network_for_rules.rules.list.return_value = [mock_rule]
    mock_network_for_rules.rules.get.return_value = mock_rule

    result = cli_runner.invoke(
        app,
        ["network", "rule", "disable", "test-network", "Allow-HTTPS"],
    )

    assert result.exit_code == 0
    mock_rule.disable.assert_called_once()


def test_rule_update_description(cli_runner, mock_client):
    """Rule update should support --description option."""
    mock_net = MagicMock()
    mock_net.key = 1
    mock_net.name = "test-network"
    mock_client.networks.list.return_value = [mock_net]
    mock_client.networks.get.return_value = mock_net

    mock_rule = MagicMock()
    mock_rule.key = 100
    mock_rule.name = "test-rule"
    mock_rule.get = lambda k, d=None: {
        "$key": 100,
        "name": "test-rule",
        "description": "New desc",
    }.get(k, d)

    mock_net.rules.list.return_value = [mock_rule]
    mock_net.rules.get.return_value = mock_rule
    mock_net.rules.update.return_value = mock_rule

    result = cli_runner.invoke(
        app,
        [
            "network",
            "rule",
            "update",
            "test-network",
            "test-rule",
            "--description",
            "New description",
        ],
    )

    assert result.exit_code == 0
    call_kwargs = mock_net.rules.update.call_args[1]
    assert call_kwargs["description"] == "New description"


def test_rule_list_wide_includes_stats(
    cli_runner, mock_client, mock_network_for_rules, mock_rule
):
    """Wide output shows packets/bytes/statistics/trace columns."""
    mock_client.networks.list.return_value = [mock_network_for_rules]
    mock_client.networks.get.return_value = mock_network_for_rules
    mock_network_for_rules.rules.list.return_value = [mock_rule]

    result = cli_runner.invoke(app, ["-o", "wide", "network", "rule", "list", "test-network"])

    assert result.exit_code == 0
    # Headers may be truncated in table output; check for partial matches
    assert "Pa" in result.output  # Packets
    assert "St" in result.output  # Stats
    assert "12" in result.output  # 12345 packets value


def test_rule_json_includes_stats(
    cli_runner, mock_client, mock_network_for_rules, mock_rule
):
    """JSON output includes statistics, trace, packets, bytes."""
    import json

    mock_client.networks.list.return_value = [mock_network_for_rules]
    mock_client.networks.get.return_value = mock_network_for_rules
    mock_network_for_rules.rules.list.return_value = [mock_rule]

    result = cli_runner.invoke(app, ["-o", "json", "network", "rule", "list", "test-network"])

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data) == 1
    assert data[0]["statistics"] is True
    assert data[0]["trace"] is False
    assert data[0]["packets"] == 12345
    assert data[0]["bytes"] == 6789012


def test_rule_stats_defaults(cli_runner, mock_client, mock_network_for_rules):
    """Missing fields default to False/0, not None."""
    import json

    # Rule with no stats fields
    rule = MagicMock()
    rule.key = 200
    rule.name = "Bare-Rule"

    def mock_get(key: str, default=None):
        return {"name": "Bare-Rule", "direction": "incoming", "action": "accept"}.get(key, default)

    rule.get = mock_get

    mock_client.networks.list.return_value = [mock_network_for_rules]
    mock_client.networks.get.return_value = mock_network_for_rules
    mock_network_for_rules.rules.list.return_value = [rule]

    result = cli_runner.invoke(app, ["-o", "json", "network", "rule", "list", "test-network"])

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data[0]["statistics"] is False
    assert data[0]["trace"] is False
    assert data[0]["packets"] == 0
    assert data[0]["bytes"] == 0
