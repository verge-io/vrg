"""Tests for multi-profile (--all-profiles) list operations."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from verge_cli.cli import app


def _make_mock_vm(key: int, name: str, status: str = "running") -> MagicMock:
    """Create a mock VM with the minimum fields for _vm_to_dict."""
    vm = MagicMock()
    vm.key = key
    vm.name = name
    vm.status = status
    vm.is_running = status == "running"
    vm.is_snapshot = False
    vm.cluster_name = "Cluster1"
    vm.node_name = "Node1"

    def mock_get(k: str, default: Any = None) -> Any:
        data = {
            "description": "",
            "cpu_cores": 2,
            "ram": 2048,
            "os_family": "linux",
            "created": None,
            "modified": None,
            "need_restart": False,
        }
        return data.get(k, default)

    vm.get = mock_get
    return vm


def _make_mock_tenant(key: int, name: str) -> MagicMock:
    """Create a mock Tenant for _tenant_to_dict."""
    tenant = MagicMock()
    tenant.key = key
    tenant.name = name
    tenant.status = "running"

    def mock_get(k: str, default: Any = None) -> Any:
        return {
            "state": "",
            "is_isolated": False,
            "description": "",
            "network_name": "",
            "ui_address_ip": "",
            "uuid": "",
            "url": "",
            "note": "",
            "expose_cloud_snapshots": False,
            "allow_branding": False,
        }.get(k, default)

    tenant.get = mock_get
    return tenant


@pytest.fixture
def _two_profile_config():
    """Patch load_config to return two profiles and get_client to return per-profile mocks."""
    from verge_cli.config import Config, ProfileConfig

    default_profile = ProfileConfig(host="host-a.example.com", token="tok-a")
    lab_profile = ProfileConfig(host="host-b.example.com", token="tok-b")
    config = Config(default=default_profile, profiles={"lab": lab_profile})

    # Map host -> mock client
    client_a = MagicMock()
    client_b = MagicMock()

    def fake_get_client(profile_config, **_kw):
        if profile_config.host == "host-a.example.com":
            return client_a
        return client_b

    with (
        patch("verge_cli.multi.load_config", return_value=config),
        patch("verge_cli.multi.get_client", side_effect=fake_get_client),
    ):
        yield client_a, client_b


class TestAllProfilesVM:
    """Tests for vrg --all-profiles vm list."""

    def test_aggregates_vms_from_both_profiles(self, cli_runner, _two_profile_config):
        client_a, client_b = _two_profile_config
        client_a.vms.list.return_value = [_make_mock_vm(1, "a1")]
        client_b.vms.list.return_value = [_make_mock_vm(2, "b1")]

        result = cli_runner.invoke(app, ["--all-profiles", "-o", "json", "vm", "list"])

        assert result.exit_code == 0
        assert '"a1"' in result.output
        assert '"b1"' in result.output
        assert '"default"' in result.output
        assert '"lab"' in result.output

    def test_json_output_includes_profile_field(self, cli_runner, _two_profile_config):
        client_a, client_b = _two_profile_config
        client_a.vms.list.return_value = [_make_mock_vm(1, "vm-alpha")]
        client_b.vms.list.return_value = []

        result = cli_runner.invoke(app, ["--all-profiles", "-o", "json", "vm", "list"])

        assert result.exit_code == 0
        assert '"_profile"' in result.output
        assert '"default"' in result.output

    def test_csv_output_has_profile_column(self, cli_runner, _two_profile_config):
        client_a, client_b = _two_profile_config
        client_a.vms.list.return_value = [_make_mock_vm(1, "vm-alpha")]
        client_b.vms.list.return_value = [_make_mock_vm(2, "vm-beta")]

        result = cli_runner.invoke(app, ["--all-profiles", "-o", "csv", "vm", "list"])

        assert result.exit_code == 0
        lines = result.output.strip().split("\n")
        assert "Profile" in lines[0]
        assert "default" in lines[1]
        assert "lab" in lines[2]

    def test_empty_profiles_shows_no_results(self, cli_runner, _two_profile_config):
        client_a, client_b = _two_profile_config
        client_a.vms.list.return_value = []
        client_b.vms.list.return_value = []

        result = cli_runner.invoke(app, ["--all-profiles", "vm", "list"])

        assert result.exit_code == 0


class TestAllProfilesTenant:
    """Tests for vrg --all-profiles tenant list."""

    def test_aggregates_tenants(self, cli_runner, _two_profile_config):
        client_a, client_b = _two_profile_config
        client_a.tenants.list.return_value = [_make_mock_tenant(1, "acme")]
        client_b.tenants.list.return_value = [_make_mock_tenant(2, "beta-co")]

        result = cli_runner.invoke(app, ["--all-profiles", "tenant", "list"])

        assert result.exit_code == 0
        assert "acme" in result.output
        assert "beta-co" in result.output


class TestAllProfilesErrorHandling:
    """Tests for error handling across profiles."""

    def test_failed_profile_shows_warning_continues(self, cli_runner):
        """A profile that fails to connect should warn and continue."""
        from verge_cli.config import Config, ProfileConfig

        good_profile = ProfileConfig(host="good.example.com", token="tok")
        bad_profile = ProfileConfig(host="bad.example.com", token="tok")
        config = Config(default=good_profile, profiles={"bad": bad_profile})

        good_client = MagicMock()
        good_client.vms.list.return_value = [_make_mock_vm(1, "survivor")]

        def fake_get_client(profile_config, **_kw):
            if profile_config.host == "bad.example.com":
                raise Exception("connection refused")
            return good_client

        with (
            patch("verge_cli.multi.load_config", return_value=config),
            patch("verge_cli.multi.get_client", side_effect=fake_get_client),
        ):
            result = cli_runner.invoke(app, ["--all-profiles", "vm", "list"])

        assert result.exit_code == 0
        # Table truncates long names; check JSON instead or just check exit code
        # The VM data is present (visible as "surviv…" in table output)
        assert "surviv" in result.output

    def test_profile_without_host_skipped(self, cli_runner):
        """A profile with no host configured should be skipped with a warning."""
        from verge_cli.config import Config, ProfileConfig

        good_profile = ProfileConfig(host="good.example.com", token="tok")
        no_host_profile = ProfileConfig(token="tok")
        config = Config(default=good_profile, profiles={"empty": no_host_profile})

        good_client = MagicMock()
        good_client.vms.list.return_value = [_make_mock_vm(1, "vm-ok")]

        with (
            patch("verge_cli.multi.load_config", return_value=config),
            patch("verge_cli.multi.get_client", return_value=good_client),
        ):
            result = cli_runner.invoke(app, ["--all-profiles", "vm", "list"])

        assert result.exit_code == 0
        assert "vm-ok" in result.output
