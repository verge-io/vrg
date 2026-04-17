"""Tests for network monitor quality/history commands."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from verge_cli.cli import app


@pytest.fixture
def mock_network_for_monitor():
    """Create a mock Network with stats manager."""
    net = MagicMock()
    net.key = 3
    net.name = "External"

    def mock_get(key: str, default=None):
        return {"running": True}.get(key, default)

    net.get = mock_get
    return net


@pytest.fixture
def mock_monitor_stats():
    """Create mock NetworkMonitorStats."""
    stats = MagicMock()
    stats.quality = 99
    stats.latency_avg_ms = 1.23
    stats.latency_peak_ms = 5.67
    stats.sent = 1000
    stats.dropped = 1
    stats.dropped_pct = 0
    stats.duplicates = 0
    stats.bad_checksums = 0
    stats.bad_data = 0
    return stats


@pytest.fixture
def mock_history_point():
    """Create a mock history point."""
    point = MagicMock()
    point.timestamp = datetime(2026, 4, 16, 12, 0, 0, tzinfo=timezone.utc)
    point.quality = 98
    point.latency_avg_ms = 2.34
    point.latency_peak_ms = 8.90
    point.dropped = 2
    point.sent = 500
    return point


def test_quality(cli_runner, mock_client, mock_network_for_monitor, mock_monitor_stats):
    """Quality command shows current network quality stats."""
    mock_client.networks.list.return_value = [mock_network_for_monitor]
    mock_client.networks.get.return_value = mock_network_for_monitor
    mock_network_for_monitor.stats.get.return_value = mock_monitor_stats

    result = cli_runner.invoke(app, ["network", "diag", "quality", "External"])

    assert result.exit_code == 0
    assert "99" in result.output


def test_quality_json(cli_runner, mock_client, mock_network_for_monitor, mock_monitor_stats):
    """JSON output includes all quality fields."""
    mock_client.networks.list.return_value = [mock_network_for_monitor]
    mock_client.networks.get.return_value = mock_network_for_monitor
    mock_network_for_monitor.stats.get.return_value = mock_monitor_stats

    result = cli_runner.invoke(app, ["-o", "json", "network", "diag", "quality", "External"])

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["quality"] == 99
    assert data["latency_avg_ms"] == 1.23
    assert data["sent"] == 1000


def test_quality_network_not_found(cli_runner, mock_client):
    """Bad network name should exit with code 6."""
    mock_client.networks.list.return_value = []

    result = cli_runner.invoke(app, ["network", "diag", "quality", "nonexistent"])

    assert result.exit_code == 6


def test_history(cli_runner, mock_client, mock_network_for_monitor, mock_history_point):
    """History shows short-term monitoring history."""
    mock_client.networks.list.return_value = [mock_network_for_monitor]
    mock_client.networks.get.return_value = mock_network_for_monitor
    mock_network_for_monitor.stats.history_short.return_value = [mock_history_point]

    result = cli_runner.invoke(app, ["network", "diag", "history", "External"])

    assert result.exit_code == 0
    mock_network_for_monitor.stats.history_short.assert_called_once_with(limit=20)
    assert "98" in result.output


def test_history_long(cli_runner, mock_client, mock_network_for_monitor, mock_history_point):
    """--long flag uses long-term history."""
    mock_client.networks.list.return_value = [mock_network_for_monitor]
    mock_client.networks.get.return_value = mock_network_for_monitor
    mock_network_for_monitor.stats.history_long.return_value = [mock_history_point]

    result = cli_runner.invoke(app, ["network", "diag", "history", "External", "--long"])

    assert result.exit_code == 0
    mock_network_for_monitor.stats.history_long.assert_called_once_with(limit=20)


def test_history_limit(cli_runner, mock_client, mock_network_for_monitor, mock_history_point):
    """--limit N passes through to SDK."""
    mock_client.networks.list.return_value = [mock_network_for_monitor]
    mock_client.networks.get.return_value = mock_network_for_monitor
    mock_network_for_monitor.stats.history_short.return_value = [mock_history_point]

    result = cli_runner.invoke(
        app, ["network", "diag", "history", "External", "--limit", "50"]
    )

    assert result.exit_code == 0
    mock_network_for_monitor.stats.history_short.assert_called_once_with(limit=50)
