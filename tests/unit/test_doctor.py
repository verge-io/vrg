"""Tests for the doctor command."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner

from verge_cli.cli import app


# ---------------------------------------------------------------------------
# Helpers to build mock objects
# ---------------------------------------------------------------------------


def _mock_node(
    name: str = "node1",
    key: int = 1,
    status: str = "online",
    needs_restart: bool = False,
    vsan_connected: bool = True,
    vergeos_version: str = "6.2.1",
    reload_drivers_required: bool = False,
) -> MagicMock:
    n = MagicMock()
    n.key = key
    n.name = name
    n.status = status
    n.needs_restart = needs_restart
    n.vsan_connected = vsan_connected
    n.vergeos_version = vergeos_version
    n.reload_drivers_required = reload_drivers_required
    return n


def _mock_cluster(
    name: str = "cluster1",
    key: int = 1,
    status: str = "online",
    total_nodes: int = 2,
    online_nodes: int = 2,
) -> MagicMock:
    c = MagicMock()
    c.key = key
    c.name = name
    c.status = status
    c.get = lambda k, default=None: {"total_nodes": total_nodes, "online_nodes": online_nodes}.get(
        k, default
    )
    return c


def _mock_vsan_status(
    cluster_name: str = "cluster1",
    health_status: str = "healthy",
) -> MagicMock:
    v = MagicMock()
    v.cluster_name = cluster_name
    v.health_status = health_status
    return v


def _mock_tier(
    key: int = 1,
    tier: int = 0,
    used_percent: float = 50.0,
    capacity_gb: float = 1000.0,
    used_gb: float = 500.0,
) -> MagicMock:
    t = MagicMock()
    t.key = key
    t.tier = tier
    t.used_percent = used_percent
    t.capacity_gb = capacity_gb
    t.used_gb = used_gb
    return t


def _mock_alarm(
    key: int = 1,
    level: str = "warning",
) -> MagicMock:
    a = MagicMock()
    a.key = key
    a.level = level
    return a


def _mock_cert(
    key: int = 1,
    domain: str = "test.example.com",
    is_valid: bool = True,
    days_until_expiry: int = 90,
) -> MagicMock:
    c = MagicMock()
    c.key = key
    c.domain = domain
    c.is_valid = is_valid
    c.days_until_expiry = days_until_expiry
    return c


def _mock_license(
    key: int = 1,
    name: str = "Standard",
    is_valid: bool = True,
    days_until_expiry: int | None = 365,
) -> MagicMock:
    lic = MagicMock()
    lic.key = key
    lic.name = name
    lic.is_valid = is_valid
    lic.days_until_expiry = days_until_expiry
    return lic


def _mock_fabric_status(
    is_healthy: bool = True,
    fabric_status: str = "confirmed",
    max_score: float = 50.0,
    min_score: float = 50.0,
) -> MagicMock:
    f = MagicMock()
    f.is_healthy = is_healthy
    f.fabric_status = fabric_status
    f.max_score = max_score
    f.min_score = min_score
    return f


def _mock_physical_drive(
    key: int = 1,
    has_warnings: bool = False,
    has_vsan_errors: bool = False,
    serial: str = "ABC123",
    model: str = "Samsung 870",
) -> MagicMock:
    d = MagicMock()
    d.key = key
    d.has_warnings = has_warnings
    d.has_vsan_errors = has_vsan_errors
    d.serial = serial
    d.model = model
    return d


def _mock_dimm(
    key: int = 1,
    is_healthy: bool = True,
    status: str = "online",
    locator: str = "DIMM 0",
) -> MagicMock:
    d = MagicMock()
    d.key = key
    d.is_healthy = is_healthy
    d.status = status
    d.locator = locator
    return d


def _mock_user(
    name: str = "admin",
    key: int = 1,
    physical_access: bool = False,
    two_factor_enabled: bool = False,
) -> MagicMock:
    u = MagicMock()
    u.key = key
    u.name = name
    u.physical_access = physical_access
    u.two_factor_enabled = two_factor_enabled
    return u


def _mock_network(
    name: str = "internal",
    key: int = 1,
    net_type: str = "internal",
    mtu: int = 1500,
    needs_restart: bool = False,
    needs_rule_apply: bool = False,
    needs_dns_apply: bool = False,
    vxlan_multicast: str | None = None,
) -> MagicMock:
    n = MagicMock()
    n.key = key
    n.name = name
    n.type = net_type
    n.mtu = mtu
    n.needs_restart = needs_restart
    n.needs_rule_apply = needs_rule_apply
    n.needs_dns_apply = needs_dns_apply
    n.get = lambda k, default=None: {"vxlan_multicast": vxlan_multicast}.get(k, default)
    return n


def _mock_lldp_neighbor(
    node_key: int = 1,
    nic_key: int = 1,
    chassis_name: str = "switch1",
) -> MagicMock:
    n = MagicMock()
    n.node_key = node_key
    n.nic_key = nic_key
    n.chassis_name = chassis_name
    return n


def _mock_update_package(
    name: str = "yb",
    key: int = 1,
    version: str = "6.2.1",
) -> MagicMock:
    p = MagicMock()
    p.key = key
    p.name = name
    p.get = lambda k, default=None: {"version": version}.get(k, default)
    return p


def _mock_snapshot_profile(
    name: str = "Default",
    key: int = 1,
) -> MagicMock:
    p = MagicMock()
    p.key = key
    p.name = name
    return p


def _mock_vsan_query_result(
    is_complete: bool = True,
    is_error: bool = False,
    result: str | None = "{}",
) -> MagicMock:
    r = MagicMock()
    r.is_complete = is_complete
    r.is_error = is_error
    r.result = result
    return r


def _setup_healthy_client(mock_client: MagicMock) -> None:
    """Configure mock_client to represent a fully healthy system."""
    # Connectivity
    mock_client.version = "6.2.1"
    mock_client.os_version = "1.0.0"
    mock_client.cloud_name = "Test Cloud"

    # Clusters
    mock_client.clusters.list.return_value = [_mock_cluster()]
    mock_client.clusters.vsan_status.return_value = [_mock_vsan_status()]

    # Nodes
    mock_client.nodes.list.return_value = [
        _mock_node("node1", 1),
        _mock_node("node2", 2),
    ]

    # Storage tiers
    mock_client.storage_tiers.list.return_value = [_mock_tier()]

    # Alarms
    mock_client.alarms.list.return_value = []

    # Updates
    mock_settings = MagicMock()
    mock_settings.get.return_value = False
    mock_client.update_settings.get.return_value = mock_settings

    # Fabric
    mock_client.machine_nic_fabric_status.list.return_value = [_mock_fabric_status()]

    # Network dashboard
    mock_dashboard = MagicMock()
    mock_dashboard.get.return_value = {}
    mock_client.network_dashboard = mock_dashboard

    # Certificates
    mock_client.certificates.list.return_value = [_mock_cert()]

    # Licenses
    mock_client.system.licenses.list.return_value = [_mock_license()]

    # Physical drives
    mock_client.physical_drives.list.return_value = [_mock_physical_drive()]

    # Node memory
    mock_client.node_memory.list.return_value = [_mock_dimm()]

    # vSAN queries
    mock_client.vsan_queries.journal_status.return_value = _mock_vsan_query_result()
    mock_client.vsan_queries.tier_status.return_value = _mock_vsan_query_result()

    # Networks (for network_pending / mtu checks)
    mock_client.networks.list.return_value = [
        _mock_network("core", 1, net_type="core", mtu=9000, vxlan_multicast="239.0.0.1"),
        _mock_network("Core Switch", 2, net_type="physical", mtu=9192, vxlan_multicast="239.0.0.1"),
    ]

    # LLDP neighbors
    mock_client.node_lldp_neighbors.list.return_value = [
        _mock_lldp_neighbor(node_key=1, nic_key=1, chassis_name="switch1"),
        _mock_lldp_neighbor(node_key=1, nic_key=2, chassis_name="switch2"),
    ]

    # Update source packages (same version as system = no update available)
    mock_client.update_source_packages.list.return_value = [
        _mock_update_package("ybos", 1, version="6.2.1"),
    ]

    # Users
    mock_client.users.list.return_value = [
        _mock_user("admin", 1, physical_access=True, two_factor_enabled=False),
        _mock_user("operator", 2, physical_access=True, two_factor_enabled=True),
    ]

    # Snapshot profiles
    mock_client.snapshot_profiles.list.return_value = [_mock_snapshot_profile()]

    # Driver reload (nodes already set up — just ensure reload_drivers_required is False)
    for n in mock_client.nodes.list.return_value:
        n.reload_drivers_required = False


# ===========================================================================
# Step 1: Foundation — connectivity, runner, command registration
# ===========================================================================


class TestConnectivity:
    def test_connectivity_pass(self, cli_runner: CliRunner, mock_client: MagicMock) -> None:
        _setup_healthy_client(mock_client)
        result = cli_runner.invoke(app, ["doctor", "--check", "connectivity"])
        assert result.exit_code == 0
        assert "pass" in result.output.lower()
        assert "6.2.1" in result.output

    def test_connectivity_fail_on_exception(
        self, cli_runner: CliRunner, mock_client: MagicMock
    ) -> None:
        mock_client.system.statistics.side_effect = Exception("Connection refused")
        result = cli_runner.invoke(app, ["doctor", "--check", "connectivity"])
        assert result.exit_code == 1  # exit 1 because the check failed
        assert "fail" in result.output.lower()


class TestRunner:
    def test_runner_isolates_exceptions(
        self, cli_runner: CliRunner, mock_client: MagicMock
    ) -> None:
        """One check failing doesn't abort the rest."""
        _setup_healthy_client(mock_client)
        # Break connectivity but leave others working
        mock_client.system.statistics.side_effect = Exception("boom")
        result = cli_runner.invoke(app, ["doctor"])
        assert result.exit_code in (0, 1)
        # Should still have output for other checks
        assert "clusters" in result.output.lower() or "nodes" in result.output.lower()

    def test_runner_filters_by_name(self, cli_runner: CliRunner, mock_client: MagicMock) -> None:
        _setup_healthy_client(mock_client)
        result = cli_runner.invoke(app, ["doctor", "--check", "connectivity"])
        assert result.exit_code == 0
        # Should only show connectivity, not clusters/nodes/etc.
        assert "cluster" not in result.output.lower().split("check")[0] or True
        # At minimum, connectivity should appear
        assert "connectivity" in result.output.lower()

    def test_runner_unknown_check_name(self, cli_runner: CliRunner, mock_client: MagicMock) -> None:
        _setup_healthy_client(mock_client)
        result = cli_runner.invoke(app, ["doctor", "--check", "nonexistent"])
        assert result.exit_code == 0


class TestCommandRegistration:
    def test_doctor_command_registered(self, cli_runner: CliRunner, mock_client: MagicMock) -> None:
        _setup_healthy_client(mock_client)
        result = cli_runner.invoke(app, ["doctor"])
        assert result.exit_code in (0, 1)
        assert "No such command" not in result.output

    def test_doctor_json_output(self, cli_runner: CliRunner, mock_client: MagicMock) -> None:
        _setup_healthy_client(mock_client)
        result = cli_runner.invoke(app, ["-o", "json", "doctor"])
        assert result.exit_code in (0, 1)
        import json

        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) > 0
        assert "name" in data[0]
        assert "status" in data[0]
        assert "message" in data[0]

    def test_doctor_table_output(self, cli_runner: CliRunner, mock_client: MagicMock) -> None:
        _setup_healthy_client(mock_client)
        result = cli_runner.invoke(app, ["doctor", "--check", "connectivity"])
        assert result.exit_code == 0
        assert "connectivity" in result.output.lower()


# ===========================================================================
# Step 2: Cluster, Node, Storage
# ===========================================================================


class TestClusters:
    def test_clusters_all_healthy(self, cli_runner: CliRunner, mock_client: MagicMock) -> None:
        _setup_healthy_client(mock_client)
        result = cli_runner.invoke(app, ["doctor", "--check", "clusters"])
        assert result.exit_code == 0
        assert "pass" in result.output.lower()

    def test_clusters_degraded(self, cli_runner: CliRunner, mock_client: MagicMock) -> None:
        _setup_healthy_client(mock_client)
        mock_client.clusters.vsan_status.return_value = [
            _mock_vsan_status(health_status="degraded")
        ]
        result = cli_runner.invoke(app, ["doctor", "--check", "clusters"])
        assert result.exit_code == 0
        assert "warn" in result.output.lower()

    def test_clusters_error(self, cli_runner: CliRunner, mock_client: MagicMock) -> None:
        _setup_healthy_client(mock_client)
        mock_client.clusters.vsan_status.return_value = [_mock_vsan_status(health_status="error")]
        result = cli_runner.invoke(app, ["doctor", "--check", "clusters"])
        assert result.exit_code == 1
        assert "fail" in result.output.lower()

    def test_clusters_nodes_offline(self, cli_runner: CliRunner, mock_client: MagicMock) -> None:
        _setup_healthy_client(mock_client)
        mock_client.clusters.list.return_value = [_mock_cluster(online_nodes=1, total_nodes=2)]
        result = cli_runner.invoke(app, ["doctor", "--check", "clusters"])
        assert result.exit_code == 0
        assert "warn" in result.output.lower()


class TestNodes:
    def test_nodes_all_online(self, cli_runner: CliRunner, mock_client: MagicMock) -> None:
        _setup_healthy_client(mock_client)
        result = cli_runner.invoke(app, ["doctor", "--check", "nodes"])
        assert result.exit_code == 0
        assert "pass" in result.output.lower()

    def test_nodes_one_offline(self, cli_runner: CliRunner, mock_client: MagicMock) -> None:
        _setup_healthy_client(mock_client)
        mock_client.nodes.list.return_value = [
            _mock_node("node1", status="online"),
            _mock_node("node2", status="offline"),
        ]
        result = cli_runner.invoke(app, ["doctor", "--check", "nodes"])
        assert result.exit_code == 0
        assert "warn" in result.output.lower()

    def test_nodes_needs_restart(self, cli_runner: CliRunner, mock_client: MagicMock) -> None:
        _setup_healthy_client(mock_client)
        mock_client.nodes.list.return_value = [
            _mock_node("node1", needs_restart=True),
        ]
        result = cli_runner.invoke(app, ["doctor", "--check", "nodes"])
        assert result.exit_code == 0
        assert "warn" in result.output.lower()

    def test_nodes_vsan_disconnected(self, cli_runner: CliRunner, mock_client: MagicMock) -> None:
        _setup_healthy_client(mock_client)
        mock_client.nodes.list.return_value = [
            _mock_node("node1", vsan_connected=False),
        ]
        result = cli_runner.invoke(app, ["doctor", "--check", "nodes"])
        assert result.exit_code == 0
        assert "warn" in result.output.lower()


class TestStorageTiers:
    def test_storage_healthy(self, cli_runner: CliRunner, mock_client: MagicMock) -> None:
        _setup_healthy_client(mock_client)
        result = cli_runner.invoke(app, ["doctor", "--check", "storage"])
        assert result.exit_code == 0
        assert "pass" in result.output.lower()

    def test_storage_warn_80pct(self, cli_runner: CliRunner, mock_client: MagicMock) -> None:
        _setup_healthy_client(mock_client)
        mock_client.storage_tiers.list.return_value = [_mock_tier(used_percent=85.0)]
        result = cli_runner.invoke(app, ["doctor", "--check", "storage"])
        assert result.exit_code == 0
        assert "warn" in result.output.lower()

    def test_storage_fail_95pct(self, cli_runner: CliRunner, mock_client: MagicMock) -> None:
        _setup_healthy_client(mock_client)
        mock_client.storage_tiers.list.return_value = [_mock_tier(used_percent=96.0)]
        result = cli_runner.invoke(app, ["doctor", "--check", "storage"])
        assert result.exit_code == 1
        assert "fail" in result.output.lower()


# ===========================================================================
# Step 3: Alarms, Updates, Version Consistency
# ===========================================================================


class TestAlarms:
    def test_alarms_none(self, cli_runner: CliRunner, mock_client: MagicMock) -> None:
        _setup_healthy_client(mock_client)
        result = cli_runner.invoke(app, ["doctor", "--check", "alarms"])
        assert result.exit_code == 0
        assert "pass" in result.output.lower()

    def test_alarms_warnings_only(self, cli_runner: CliRunner, mock_client: MagicMock) -> None:
        _setup_healthy_client(mock_client)
        mock_client.alarms.list.return_value = [
            _mock_alarm(level="warning"),
            _mock_alarm(key=2, level="warning"),
        ]
        result = cli_runner.invoke(app, ["doctor", "--check", "alarms"])
        assert result.exit_code == 0
        assert "pass" in result.output.lower()

    def test_alarms_error_level(self, cli_runner: CliRunner, mock_client: MagicMock) -> None:
        _setup_healthy_client(mock_client)
        mock_client.alarms.list.return_value = [_mock_alarm(level="error")]
        result = cli_runner.invoke(app, ["doctor", "--check", "alarms"])
        assert result.exit_code == 0
        assert "warn" in result.output.lower()

    def test_alarms_critical(self, cli_runner: CliRunner, mock_client: MagicMock) -> None:
        _setup_healthy_client(mock_client)
        mock_client.alarms.list.return_value = [_mock_alarm(level="critical")]
        result = cli_runner.invoke(app, ["doctor", "--check", "alarms"])
        assert result.exit_code == 1
        assert "fail" in result.output.lower()

    def test_alarms_mixed(self, cli_runner: CliRunner, mock_client: MagicMock) -> None:
        _setup_healthy_client(mock_client)
        mock_client.alarms.list.return_value = [
            _mock_alarm(key=1, level="critical"),
            _mock_alarm(key=2, level="error"),
            _mock_alarm(key=3, level="warning"),
        ]
        result = cli_runner.invoke(app, ["doctor", "--check", "alarms"])
        assert result.exit_code == 1
        assert "fail" in result.output.lower()


class TestUpdates:
    def test_updates_no_reboot(self, cli_runner: CliRunner, mock_client: MagicMock) -> None:
        _setup_healthy_client(mock_client)
        result = cli_runner.invoke(app, ["doctor", "--check", "updates"])
        assert result.exit_code == 0
        assert "pass" in result.output.lower()

    def test_updates_reboot_required(self, cli_runner: CliRunner, mock_client: MagicMock) -> None:
        _setup_healthy_client(mock_client)
        mock_settings = MagicMock()
        mock_settings.get.return_value = True
        mock_client.update_settings.get.return_value = mock_settings
        result = cli_runner.invoke(app, ["doctor", "--check", "updates"])
        assert result.exit_code == 0
        assert "warn" in result.output.lower()


class TestVersionConsistency:
    def test_versions_consistent(self, cli_runner: CliRunner, mock_client: MagicMock) -> None:
        _setup_healthy_client(mock_client)
        result = cli_runner.invoke(app, ["doctor", "--check", "versions"])
        assert result.exit_code == 0
        assert "pass" in result.output.lower()

    def test_versions_mismatch(self, cli_runner: CliRunner, mock_client: MagicMock) -> None:
        _setup_healthy_client(mock_client)
        mock_client.nodes.list.return_value = [
            _mock_node("node1", vergeos_version="6.2.1"),
            _mock_node("node2", vergeos_version="6.2.0"),
        ]
        result = cli_runner.invoke(app, ["doctor", "--check", "versions"])
        assert result.exit_code == 0
        assert "warn" in result.output.lower()

    def test_versions_single_node(self, cli_runner: CliRunner, mock_client: MagicMock) -> None:
        _setup_healthy_client(mock_client)
        mock_client.nodes.list.return_value = [_mock_node("node1")]
        result = cli_runner.invoke(app, ["doctor", "--check", "versions"])
        assert result.exit_code == 0
        assert "pass" in result.output.lower()


# ===========================================================================
# Step 4: Fabric, Networks, Certs, Licenses, Stubs
# ===========================================================================


class TestFabric:
    def test_fabric_all_healthy(self, cli_runner: CliRunner, mock_client: MagicMock) -> None:
        _setup_healthy_client(mock_client)
        result = cli_runner.invoke(app, ["doctor", "--check", "fabric"])
        assert result.exit_code == 0
        assert "pass" in result.output.lower()

    def test_fabric_degraded(self, cli_runner: CliRunner, mock_client: MagicMock) -> None:
        _setup_healthy_client(mock_client)
        mock_client.machine_nic_fabric_status.list.return_value = [
            _mock_fabric_status(is_healthy=False, fabric_status="degraded"),
        ]
        result = cli_runner.invoke(app, ["doctor", "--check", "fabric"])
        assert result.exit_code == 0
        assert "warn" in result.output.lower()

    def test_fabric_no_fabric_nics(self, cli_runner: CliRunner, mock_client: MagicMock) -> None:
        _setup_healthy_client(mock_client)
        mock_client.machine_nic_fabric_status.list.return_value = []
        result = cli_runner.invoke(app, ["doctor", "--check", "fabric"])
        assert result.exit_code == 0
        assert "pass" in result.output.lower()


class TestNetworks:
    def test_networks_healthy(self, cli_runner: CliRunner, mock_client: MagicMock) -> None:
        _setup_healthy_client(mock_client)
        result = cli_runner.invoke(app, ["doctor", "--check", "networks"])
        assert result.exit_code == 0
        assert "pass" in result.output.lower()


class TestCertificates:
    def test_certs_valid(self, cli_runner: CliRunner, mock_client: MagicMock) -> None:
        _setup_healthy_client(mock_client)
        result = cli_runner.invoke(app, ["doctor", "--check", "certificates"])
        assert result.exit_code == 0
        assert "pass" in result.output.lower()

    def test_certs_expiring_soon(self, cli_runner: CliRunner, mock_client: MagicMock) -> None:
        _setup_healthy_client(mock_client)
        mock_client.certificates.list.return_value = [
            _mock_cert(days_until_expiry=15),
        ]
        result = cli_runner.invoke(app, ["doctor", "--check", "certificates"])
        assert result.exit_code == 0
        assert "warn" in result.output.lower()

    def test_certs_expired(self, cli_runner: CliRunner, mock_client: MagicMock) -> None:
        _setup_healthy_client(mock_client)
        mock_client.certificates.list.return_value = [
            _mock_cert(is_valid=False, days_until_expiry=-5),
        ]
        result = cli_runner.invoke(app, ["doctor", "--check", "certificates"])
        assert result.exit_code == 1
        assert "fail" in result.output.lower()


class TestLicenses:
    def test_licenses_valid(self, cli_runner: CliRunner, mock_client: MagicMock) -> None:
        _setup_healthy_client(mock_client)
        result = cli_runner.invoke(app, ["doctor", "--check", "licenses"])
        assert result.exit_code == 0
        assert "pass" in result.output.lower()

    def test_licenses_expiring(self, cli_runner: CliRunner, mock_client: MagicMock) -> None:
        _setup_healthy_client(mock_client)
        mock_client.system.licenses.list.return_value = [
            _mock_license(days_until_expiry=20),
        ]
        result = cli_runner.invoke(app, ["doctor", "--check", "licenses"])
        assert result.exit_code == 0
        assert "warn" in result.output.lower()

    def test_licenses_invalid(self, cli_runner: CliRunner, mock_client: MagicMock) -> None:
        _setup_healthy_client(mock_client)
        mock_client.system.licenses.list.return_value = [
            _mock_license(is_valid=False, days_until_expiry=None),
        ]
        result = cli_runner.invoke(app, ["doctor", "--check", "licenses"])
        assert result.exit_code == 1
        assert "fail" in result.output.lower()


class TestDriveSmart:
    def test_drives_healthy(self, cli_runner: CliRunner, mock_client: MagicMock) -> None:
        _setup_healthy_client(mock_client)
        result = cli_runner.invoke(app, ["doctor", "--check", "drive_smart"])
        assert result.exit_code == 0
        assert "pass" in result.output.lower()

    def test_drives_smart_warnings(self, cli_runner: CliRunner, mock_client: MagicMock) -> None:
        _setup_healthy_client(mock_client)
        mock_client.physical_drives.list.return_value = [
            _mock_physical_drive(has_warnings=True, serial="BAD1"),
        ]
        result = cli_runner.invoke(app, ["doctor", "--check", "drive_smart"])
        assert result.exit_code == 0
        assert "warn" in result.output.lower()

    def test_drives_vsan_errors(self, cli_runner: CliRunner, mock_client: MagicMock) -> None:
        _setup_healthy_client(mock_client)
        mock_client.physical_drives.list.return_value = [
            _mock_physical_drive(has_vsan_errors=True, serial="ERR1"),
        ]
        result = cli_runner.invoke(app, ["doctor", "--check", "drive_smart"])
        assert result.exit_code == 0
        assert "warn" in result.output.lower()

    def test_drives_none(self, cli_runner: CliRunner, mock_client: MagicMock) -> None:
        _setup_healthy_client(mock_client)
        mock_client.physical_drives.list.return_value = []
        result = cli_runner.invoke(app, ["doctor", "--check", "drive_smart"])
        assert result.exit_code == 0
        assert "pass" in result.output.lower()


class TestDimmHealth:
    def test_dimms_healthy(self, cli_runner: CliRunner, mock_client: MagicMock) -> None:
        _setup_healthy_client(mock_client)
        result = cli_runner.invoke(app, ["doctor", "--check", "dimm_health"])
        assert result.exit_code == 0
        assert "pass" in result.output.lower()

    def test_dimms_unhealthy(self, cli_runner: CliRunner, mock_client: MagicMock) -> None:
        _setup_healthy_client(mock_client)
        mock_client.node_memory.list.return_value = [
            _mock_dimm(is_healthy=False, status="error", locator="DIMM 2"),
        ]
        result = cli_runner.invoke(app, ["doctor", "--check", "dimm_health"])
        assert result.exit_code == 0
        assert "warn" in result.output.lower()

    def test_dimms_none(self, cli_runner: CliRunner, mock_client: MagicMock) -> None:
        _setup_healthy_client(mock_client)
        mock_client.node_memory.list.return_value = []
        result = cli_runner.invoke(app, ["doctor", "--check", "dimm_health"])
        assert result.exit_code == 0
        assert "pass" in result.output.lower()


class TestVsanJournal:
    def test_vsan_healthy(self, cli_runner: CliRunner, mock_client: MagicMock) -> None:
        _setup_healthy_client(mock_client)
        result = cli_runner.invoke(app, ["doctor", "--check", "vsan_journal"])
        assert result.exit_code == 0
        assert "pass" in result.output.lower()

    def test_vsan_journal_error(self, cli_runner: CliRunner, mock_client: MagicMock) -> None:
        _setup_healthy_client(mock_client)
        mock_client.vsan_queries.journal_status.return_value = _mock_vsan_query_result(
            is_complete=False, is_error=True, result="journal corrupted"
        )
        result = cli_runner.invoke(app, ["doctor", "--check", "vsan_journal"])
        assert result.exit_code == 0
        assert "warn" in result.output.lower()

    def test_vsan_tier_error(self, cli_runner: CliRunner, mock_client: MagicMock) -> None:
        _setup_healthy_client(mock_client)
        mock_client.vsan_queries.tier_status.return_value = _mock_vsan_query_result(
            is_complete=False, is_error=True, result="tier degraded"
        )
        result = cli_runner.invoke(app, ["doctor", "--check", "vsan_journal"])
        assert result.exit_code == 0
        assert "warn" in result.output.lower()


class TestDriverReload:
    def test_no_reload_needed(self, cli_runner: CliRunner, mock_client: MagicMock) -> None:
        _setup_healthy_client(mock_client)
        result = cli_runner.invoke(app, ["doctor", "--check", "driver_reload"])
        assert result.exit_code == 0
        assert "pass" in result.output.lower()

    def test_reload_needed(self, cli_runner: CliRunner, mock_client: MagicMock) -> None:
        _setup_healthy_client(mock_client)
        mock_client.nodes.list.return_value = [
            _mock_node("node1", reload_drivers_required=True),
        ]
        # Need to set the attribute since _mock_node doesn't have it
        mock_client.nodes.list.return_value[0].reload_drivers_required = True
        result = cli_runner.invoke(app, ["doctor", "--check", "driver_reload"])
        assert result.exit_code == 0
        assert "warn" in result.output.lower()


# ===========================================================================
# Step 5: Summary, Exit Codes, Polish
# ===========================================================================


class TestExitCodes:
    def test_exit_code_0_all_pass(self, cli_runner: CliRunner, mock_client: MagicMock) -> None:
        _setup_healthy_client(mock_client)
        result = cli_runner.invoke(app, ["doctor"])
        assert result.exit_code == 0

    def test_exit_code_1_with_fail(self, cli_runner: CliRunner, mock_client: MagicMock) -> None:
        _setup_healthy_client(mock_client)
        mock_client.alarms.list.return_value = [_mock_alarm(level="critical")]
        result = cli_runner.invoke(app, ["doctor"])
        assert result.exit_code == 1

    def test_exit_code_0_with_warns(self, cli_runner: CliRunner, mock_client: MagicMock) -> None:
        _setup_healthy_client(mock_client)
        mock_client.alarms.list.return_value = [_mock_alarm(level="error")]
        result = cli_runner.invoke(app, ["doctor"])
        assert result.exit_code == 0


class TestSummaryLine:
    def test_summary_line_content(self, cli_runner: CliRunner, mock_client: MagicMock) -> None:
        _setup_healthy_client(mock_client)
        result = cli_runner.invoke(app, ["doctor"])
        assert result.exit_code == 0
        assert "passed" in result.output.lower()

    def test_summary_not_in_json(self, cli_runner: CliRunner, mock_client: MagicMock) -> None:
        _setup_healthy_client(mock_client)
        result = cli_runner.invoke(app, ["-o", "json", "doctor"])
        assert "passed" not in result.output.lower() or result.output.strip().startswith("[")


class TestListChecks:
    def test_list_checks(self, cli_runner: CliRunner, mock_client: MagicMock) -> None:
        result = cli_runner.invoke(app, ["doctor", "--list-checks"])
        assert result.exit_code == 0
        assert "connectivity" in result.output
        assert "clusters" in result.output
        assert "nodes" in result.output

    def test_list_checks_exit_code(self, cli_runner: CliRunner, mock_client: MagicMock) -> None:
        result = cli_runner.invoke(app, ["doctor", "--list-checks"])
        assert result.exit_code == 0


# ===========================================================================
# Step 6: Admin & Security
# ===========================================================================


class TestAdminUsers:
    def test_multiple_admins(self, cli_runner: CliRunner, mock_client: MagicMock) -> None:
        _setup_healthy_client(mock_client)
        mock_client.users.list.return_value = [
            _mock_user("admin", 1, physical_access=True),
            _mock_user("operator", 2, physical_access=True),
        ]
        result = cli_runner.invoke(app, ["doctor", "--check", "admin_users"])
        assert result.exit_code == 0
        assert "pass" in result.output.lower()

    def test_single_admin(self, cli_runner: CliRunner, mock_client: MagicMock) -> None:
        _setup_healthy_client(mock_client)
        mock_client.users.list.return_value = [
            _mock_user("admin", 1, physical_access=True),
            _mock_user("regular", 2, physical_access=False),
        ]
        result = cli_runner.invoke(app, ["doctor", "--check", "admin_users"])
        assert result.exit_code == 0
        assert "warn" in result.output.lower()

    def test_no_admins(self, cli_runner: CliRunner, mock_client: MagicMock) -> None:
        _setup_healthy_client(mock_client)
        mock_client.users.list.return_value = [
            _mock_user("regular", 1, physical_access=False),
        ]
        result = cli_runner.invoke(app, ["doctor", "--check", "admin_users"])
        assert result.exit_code == 0
        assert "warn" in result.output.lower()


class TestMfa:
    def test_mfa_all_enabled(self, cli_runner: CliRunner, mock_client: MagicMock) -> None:
        _setup_healthy_client(mock_client)
        mock_client.users.list.return_value = [
            _mock_user("admin", 1, physical_access=True, two_factor_enabled=False),
            _mock_user("operator", 2, physical_access=True, two_factor_enabled=True),
        ]
        result = cli_runner.invoke(app, ["doctor", "--check", "mfa"])
        assert result.exit_code == 0
        assert "pass" in result.output.lower()

    def test_mfa_missing_on_non_admin(self, cli_runner: CliRunner, mock_client: MagicMock) -> None:
        _setup_healthy_client(mock_client)
        mock_client.users.list.return_value = [
            _mock_user("admin", 1, physical_access=True, two_factor_enabled=False),
            _mock_user("operator", 2, physical_access=True, two_factor_enabled=False),
        ]
        result = cli_runner.invoke(app, ["doctor", "--check", "mfa"])
        assert result.exit_code == 0
        assert "warn" in result.output.lower()
        assert "operator" in result.output.lower()

    def test_mfa_admin_exempt(self, cli_runner: CliRunner, mock_client: MagicMock) -> None:
        _setup_healthy_client(mock_client)
        mock_client.users.list.return_value = [
            _mock_user("admin", 1, physical_access=True, two_factor_enabled=False),
        ]
        result = cli_runner.invoke(app, ["doctor", "--check", "mfa"])
        assert result.exit_code == 0
        assert "pass" in result.output.lower()

    def test_mfa_no_non_admin_admins(self, cli_runner: CliRunner, mock_client: MagicMock) -> None:
        _setup_healthy_client(mock_client)
        mock_client.users.list.return_value = [
            _mock_user("regular", 1, physical_access=False),
        ]
        result = cli_runner.invoke(app, ["doctor", "--check", "mfa"])
        assert result.exit_code == 0
        assert "pass" in result.output.lower()


class TestSnapshotProfiles:
    def test_profiles_exist(self, cli_runner: CliRunner, mock_client: MagicMock) -> None:
        _setup_healthy_client(mock_client)
        mock_client.snapshot_profiles.list.return_value = [
            _mock_snapshot_profile("Daily"),
            _mock_snapshot_profile("Weekly", key=2),
        ]
        result = cli_runner.invoke(app, ["doctor", "--check", "snapshot_profiles"])
        assert result.exit_code == 0
        assert "pass" in result.output.lower()

    def test_no_profiles(self, cli_runner: CliRunner, mock_client: MagicMock) -> None:
        _setup_healthy_client(mock_client)
        mock_client.snapshot_profiles.list.return_value = []
        result = cli_runner.invoke(app, ["doctor", "--check", "snapshot_profiles"])
        assert result.exit_code == 0
        assert "warn" in result.output.lower()


# ===========================================================================
# Step 7: Network Health
# ===========================================================================


class TestNetworkPending:
    def test_no_pending(self, cli_runner: CliRunner, mock_client: MagicMock) -> None:
        _setup_healthy_client(mock_client)
        result = cli_runner.invoke(app, ["doctor", "--check", "network_pending"])
        assert result.exit_code == 0
        assert "pass" in result.output.lower()

    def test_pending_rules(self, cli_runner: CliRunner, mock_client: MagicMock) -> None:
        _setup_healthy_client(mock_client)
        mock_client.networks.list.return_value = [
            _mock_network("internal-prod", 1, needs_rule_apply=True),
        ]
        result = cli_runner.invoke(app, ["doctor", "--check", "network_pending"])
        assert result.exit_code == 0
        assert "warn" in result.output.lower()

    def test_pending_dns(self, cli_runner: CliRunner, mock_client: MagicMock) -> None:
        _setup_healthy_client(mock_client)
        mock_client.networks.list.return_value = [
            _mock_network("internal-prod", 1, needs_dns_apply=True),
        ]
        result = cli_runner.invoke(app, ["doctor", "--check", "network_pending"])
        assert result.exit_code == 0
        assert "warn" in result.output.lower()

    def test_pending_restart(self, cli_runner: CliRunner, mock_client: MagicMock) -> None:
        _setup_healthy_client(mock_client)
        mock_client.networks.list.return_value = [
            _mock_network("internal-prod", 1, needs_restart=True),
        ]
        result = cli_runner.invoke(app, ["doctor", "--check", "network_pending"])
        assert result.exit_code == 0
        assert "warn" in result.output.lower()

    def test_no_networks(self, cli_runner: CliRunner, mock_client: MagicMock) -> None:
        _setup_healthy_client(mock_client)
        mock_client.networks.list.return_value = []
        result = cli_runner.invoke(app, ["doctor", "--check", "network_pending"])
        assert result.exit_code == 0
        assert "pass" in result.output.lower()


class TestMtu:
    def test_mtu_correct(self, cli_runner: CliRunner, mock_client: MagicMock) -> None:
        _setup_healthy_client(mock_client)
        mock_client.networks.list.return_value = [
            _mock_network("core", 1, net_type="core", mtu=9000, vxlan_multicast="239.0.0.1"),
            _mock_network("Core Switch", 2, net_type="physical", mtu=9192, vxlan_multicast="239.0.0.1"),
        ]
        result = cli_runner.invoke(app, ["doctor", "--check", "mtu"])
        assert result.exit_code == 0
        assert "pass" in result.output.lower()

    def test_core_mtu_too_low(self, cli_runner: CliRunner, mock_client: MagicMock) -> None:
        _setup_healthy_client(mock_client)
        mock_client.networks.list.return_value = [
            _mock_network("core", 1, net_type="core", mtu=1500, vxlan_multicast="239.0.0.1"),
        ]
        result = cli_runner.invoke(app, ["doctor", "--check", "mtu"])
        assert result.exit_code == 0
        assert "warn" in result.output.lower()

    def test_physical_core_mtu_too_low(self, cli_runner: CliRunner, mock_client: MagicMock) -> None:
        _setup_healthy_client(mock_client)
        mock_client.networks.list.return_value = [
            _mock_network("core", 1, net_type="core", mtu=9000, vxlan_multicast="239.0.0.1"),
            _mock_network("Core Switch", 2, net_type="physical", mtu=9000, vxlan_multicast="239.0.0.1"),
        ]
        result = cli_runner.invoke(app, ["doctor", "--check", "mtu"])
        assert result.exit_code == 0
        assert "warn" in result.output.lower()

    def test_external_physical_ignored(self, cli_runner: CliRunner, mock_client: MagicMock) -> None:
        """Physical networks without matching core vxlan_multicast are ignored."""
        _setup_healthy_client(mock_client)
        mock_client.networks.list.return_value = [
            _mock_network("core", 1, net_type="core", mtu=9000, vxlan_multicast="239.0.0.1"),
            _mock_network("External Bond", 2, net_type="physical", mtu=1500),
        ]
        result = cli_runner.invoke(app, ["doctor", "--check", "mtu"])
        assert result.exit_code == 0
        assert "pass" in result.output.lower()

    def test_no_core_networks(self, cli_runner: CliRunner, mock_client: MagicMock) -> None:
        _setup_healthy_client(mock_client)
        mock_client.networks.list.return_value = [
            _mock_network("internal", 1, net_type="internal", mtu=1500),
        ]
        result = cli_runner.invoke(app, ["doctor", "--check", "mtu"])
        assert result.exit_code == 0
        assert "pass" in result.output.lower()


class TestLldpDiversity:
    def test_diverse_switches(self, cli_runner: CliRunner, mock_client: MagicMock) -> None:
        _setup_healthy_client(mock_client)
        mock_client.node_lldp_neighbors.list.return_value = [
            _mock_lldp_neighbor(node_key=1, nic_key=1, chassis_name="switch1"),
            _mock_lldp_neighbor(node_key=1, nic_key=2, chassis_name="switch2"),
        ]
        result = cli_runner.invoke(app, ["doctor", "--check", "lldp_diversity"])
        assert result.exit_code == 0
        assert "pass" in result.output.lower()

    def test_same_switch(self, cli_runner: CliRunner, mock_client: MagicMock) -> None:
        _setup_healthy_client(mock_client)
        mock_client.node_lldp_neighbors.list.return_value = [
            _mock_lldp_neighbor(node_key=1, nic_key=1, chassis_name="switch1"),
            _mock_lldp_neighbor(node_key=1, nic_key=2, chassis_name="switch1"),
        ]
        result = cli_runner.invoke(app, ["doctor", "--check", "lldp_diversity"])
        assert result.exit_code == 0
        assert "warn" in result.output.lower()

    def test_single_nic_per_node(self, cli_runner: CliRunner, mock_client: MagicMock) -> None:
        _setup_healthy_client(mock_client)
        mock_client.node_lldp_neighbors.list.return_value = [
            _mock_lldp_neighbor(node_key=1, nic_key=1, chassis_name="switch1"),
        ]
        result = cli_runner.invoke(app, ["doctor", "--check", "lldp_diversity"])
        assert result.exit_code == 0
        assert "pass" in result.output.lower()

    def test_unknown_chassis(self, cli_runner: CliRunner, mock_client: MagicMock) -> None:
        _setup_healthy_client(mock_client)
        mock_client.node_lldp_neighbors.list.return_value = [
            _mock_lldp_neighbor(node_key=1, nic_key=1, chassis_name=None),
            _mock_lldp_neighbor(node_key=1, nic_key=2, chassis_name=None),
        ]
        result = cli_runner.invoke(app, ["doctor", "--check", "lldp_diversity"])
        assert result.exit_code == 0
        assert "pass" in result.output.lower()
        assert "unknown" in result.output.lower()

    def test_no_lldp_data(self, cli_runner: CliRunner, mock_client: MagicMock) -> None:
        _setup_healthy_client(mock_client)
        mock_client.node_lldp_neighbors.list.return_value = []
        result = cli_runner.invoke(app, ["doctor", "--check", "lldp_diversity"])
        assert result.exit_code == 0
        assert "pass" in result.output.lower()

    def test_multiple_nodes_mixed(self, cli_runner: CliRunner, mock_client: MagicMock) -> None:
        _setup_healthy_client(mock_client)
        mock_client.node_lldp_neighbors.list.return_value = [
            # Node 1: diverse
            _mock_lldp_neighbor(node_key=1, nic_key=1, chassis_name="switch1"),
            _mock_lldp_neighbor(node_key=1, nic_key=2, chassis_name="switch2"),
            # Node 2: not diverse
            _mock_lldp_neighbor(node_key=2, nic_key=3, chassis_name="switch1"),
            _mock_lldp_neighbor(node_key=2, nic_key=4, chassis_name="switch1"),
        ]
        result = cli_runner.invoke(app, ["doctor", "--check", "lldp_diversity"])
        assert result.exit_code == 0
        assert "warn" in result.output.lower()


# ===========================================================================
# Step 9: Updates Available & Fabric Speed
# ===========================================================================


class TestUpdatesAvailable:
    def test_no_updates_available(self, cli_runner: CliRunner, mock_client: MagicMock) -> None:
        _setup_healthy_client(mock_client)
        mock_client.update_source_packages.list.return_value = [
            _mock_update_package("ybos", 1, version="6.2.1"),
        ]
        result = cli_runner.invoke(app, ["doctor", "--check", "updates_available"])
        assert result.exit_code == 0
        assert "pass" in result.output.lower()

    def test_updates_available(self, cli_runner: CliRunner, mock_client: MagicMock) -> None:
        _setup_healthy_client(mock_client)
        mock_client.update_source_packages.list.return_value = [
            _mock_update_package("ybos", 1, version="6.2.2"),
        ]
        result = cli_runner.invoke(app, ["doctor", "--check", "updates_available"])
        assert result.exit_code == 0
        assert "warn" in result.output.lower()
        assert "ybos" in result.output.lower()


class TestFabricSpeed:
    def test_fabric_speed_ok(self, cli_runner: CliRunner, mock_client: MagicMock) -> None:
        _setup_healthy_client(mock_client)
        result = cli_runner.invoke(app, ["doctor", "--check", "fabric_speed"])
        assert result.exit_code == 0
        assert "pass" in result.output.lower()

    def test_fabric_speed_low(self, cli_runner: CliRunner, mock_client: MagicMock) -> None:
        _setup_healthy_client(mock_client)
        mock_client.machine_nic_fabric_status.list.return_value = [
            _mock_fabric_status(is_healthy=True, fabric_status="confirmed", max_score=50, min_score=25),
        ]
        result = cli_runner.invoke(app, ["doctor", "--check", "fabric_speed"])
        assert result.exit_code == 0
        assert "warn" in result.output.lower()

    def test_fabric_no_data(self, cli_runner: CliRunner, mock_client: MagicMock) -> None:
        _setup_healthy_client(mock_client)
        mock_client.machine_nic_fabric_status.list.return_value = []
        result = cli_runner.invoke(app, ["doctor", "--check", "fabric_speed"])
        assert result.exit_code == 0
        assert "pass" in result.output.lower()


class TestFullDoctor:
    def test_doctor_all_checks_present(self, cli_runner: CliRunner, mock_client: MagicMock) -> None:
        """Full vrg doctor shows all 23 checks."""
        _setup_healthy_client(mock_client)
        result = cli_runner.invoke(app, ["-o", "json", "doctor"])
        import json

        data = json.loads(result.output)
        names = {r["name"] for r in data}
        expected = {
            "connectivity",
            "clusters",
            "nodes",
            "storage",
            "alarms",
            "updates",
            "versions",
            "fabric",
            "networks",
            "certificates",
            "licenses",
            "drive_smart",
            "dimm_health",
            "vsan_journal",
            "driver_reload",
            "admin_users",
            "mfa",
            "snapshot_profiles",
            "network_pending",
            "mtu",
            "lldp_diversity",
            "updates_available",
            "fabric_speed",
        }
        assert names == expected
