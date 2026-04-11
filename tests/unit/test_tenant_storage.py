"""Tests for tenant storage sub-resource commands."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from verge_cli.cli import app


@pytest.fixture
def mock_tenant_storage() -> MagicMock:
    """Create a mock Tenant Storage object."""
    storage = MagicMock()
    storage.key = 200
    storage.name = "Tier 3 Storage"
    storage.tier_name = "Tier 3"
    storage.provisioned_gb = 500
    storage.used_gb = 120
    storage.used_percent = 24.0

    def mock_get(key: str, default: Any = None) -> Any:
        data = {
            "$key": 200,
            "name": "Tier 3 Storage",
            "tier_name": "Tier 3",
            "tier": 3,
            "provisioned_gb": 500,
            "used_gb": 120,
            "used_percent": 24.0,
        }
        return data.get(key, default)

    storage.get = mock_get
    return storage


def test_tenant_storage_list(cli_runner, mock_client, mock_tenant, mock_tenant_storage):
    """vrg tenant storage list should list storage allocations."""
    mock_client.tenants.list.return_value = [mock_tenant]
    mock_client.tenants.get.return_value = mock_tenant
    mock_tenant.storage.list.return_value = [mock_tenant_storage]

    result = cli_runner.invoke(app, ["tenant", "storage", "list", "acme-corp"])

    assert result.exit_code == 0
    assert "Tier 3" in result.output
    mock_tenant.storage.list.assert_called_once()


def test_tenant_storage_get(cli_runner, mock_client, mock_tenant, mock_tenant_storage):
    """vrg tenant storage get should show storage details."""
    mock_client.tenants.list.return_value = [mock_tenant]
    mock_client.tenants.get.return_value = mock_tenant
    mock_tenant.storage.list.return_value = [mock_tenant_storage]
    mock_tenant.storage.get.return_value = mock_tenant_storage

    result = cli_runner.invoke(app, ["tenant", "storage", "get", "acme-corp", "Tier 3 Storage"])

    assert result.exit_code == 0
    assert "Tier 3" in result.output


def test_tenant_storage_get_by_key(cli_runner, mock_client, mock_tenant, mock_tenant_storage):
    """vrg tenant storage get should accept numeric key."""
    mock_client.tenants.list.return_value = [mock_tenant]
    mock_client.tenants.get.return_value = mock_tenant
    mock_tenant.storage.get.return_value = mock_tenant_storage

    result = cli_runner.invoke(app, ["tenant", "storage", "get", "acme-corp", "200"])

    assert result.exit_code == 0


def test_tenant_storage_create(cli_runner, mock_client, mock_tenant, mock_tenant_storage):
    """vrg tenant storage create should allocate storage."""
    mock_client.tenants.list.return_value = [mock_tenant]
    mock_client.tenants.get.return_value = mock_tenant
    mock_tenant.storage.create.return_value = mock_tenant_storage

    result = cli_runner.invoke(
        app,
        [
            "tenant",
            "storage",
            "create",
            "acme-corp",
            "--tier",
            "3",
            "--provisioned-gb",
            "500",
        ],
    )

    assert result.exit_code == 0
    mock_tenant.storage.create.assert_called_once()
    call_kwargs = mock_tenant.storage.create.call_args[1]
    assert call_kwargs["tier"] == 3
    assert call_kwargs["provisioned_gb"] == 500


def test_tenant_storage_update(cli_runner, mock_client, mock_tenant, mock_tenant_storage):
    """vrg tenant storage update should modify storage."""
    mock_client.tenants.list.return_value = [mock_tenant]
    mock_client.tenants.get.return_value = mock_tenant
    mock_tenant.storage.list.return_value = [mock_tenant_storage]
    mock_tenant.storage.update.return_value = mock_tenant_storage

    result = cli_runner.invoke(
        app,
        [
            "tenant",
            "storage",
            "update",
            "acme-corp",
            "Tier 3 Storage",
            "--provisioned-gb",
            "1000",
        ],
    )

    assert result.exit_code == 0
    mock_tenant.storage.update.assert_called_once()
    call_args = mock_tenant.storage.update.call_args
    assert call_args[1]["provisioned"] == 1000 * 1073741824


def test_tenant_storage_update_no_changes(
    cli_runner, mock_client, mock_tenant, mock_tenant_storage
):
    """vrg tenant storage update with no flags should exit 2."""
    mock_client.tenants.list.return_value = [mock_tenant]
    mock_client.tenants.get.return_value = mock_tenant
    mock_tenant.storage.list.return_value = [mock_tenant_storage]

    result = cli_runner.invoke(app, ["tenant", "storage", "update", "acme-corp", "Tier 3 Storage"])

    assert result.exit_code == 2


def test_tenant_storage_delete(cli_runner, mock_client, mock_tenant, mock_tenant_storage):
    """vrg tenant storage delete should remove storage with --yes."""
    mock_client.tenants.list.return_value = [mock_tenant]
    mock_client.tenants.get.return_value = mock_tenant
    mock_tenant.storage.list.return_value = [mock_tenant_storage]

    result = cli_runner.invoke(
        app,
        ["tenant", "storage", "delete", "acme-corp", "Tier 3 Storage", "--yes"],
    )

    assert result.exit_code == 0
    mock_tenant.storage.delete.assert_called_once_with(200)


def test_tenant_storage_list_empty(cli_runner, mock_client, mock_tenant):
    """vrg tenant storage list should handle empty list."""
    mock_client.tenants.list.return_value = [mock_tenant]
    mock_client.tenants.get.return_value = mock_tenant
    mock_tenant.storage.list.return_value = []

    result = cli_runner.invoke(app, ["tenant", "storage", "list", "acme-corp"])

    assert result.exit_code == 0
