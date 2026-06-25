"""Tests for VM CRUD operations (list, create, update, delete, start, stop, restart)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from verge_cli.cli import app


def test_vm_list_basic(cli_runner, mock_client, mock_vm):
    """vrg vm list should list all VMs."""
    mock_client.vms.list.return_value = [mock_vm]

    result = cli_runner.invoke(app, ["vm", "list"])

    assert result.exit_code == 0
    assert "test-vm" in result.output
    mock_client.vms.list.assert_called_once_with(filter=None)


def test_vm_list_with_status_filter(cli_runner, mock_client, mock_vm):
    """vrg vm list --status running should filter by status."""
    mock_client.vms.list.return_value = [mock_vm]

    result = cli_runner.invoke(app, ["vm", "list", "--status", "running"])

    assert result.exit_code == 0
    mock_client.vms.list.assert_called_once_with(filter="status eq 'running'")


def test_vm_list_with_odata_filter(cli_runner, mock_client, mock_vm):
    """vrg vm list --filter should pass OData filter."""
    mock_client.vms.list.return_value = [mock_vm]

    result = cli_runner.invoke(app, ["vm", "list", "--filter", "name eq 'foo'"])

    assert result.exit_code == 0
    mock_client.vms.list.assert_called_once_with(filter="name eq 'foo'")


def test_vm_list_with_status_and_filter(cli_runner, mock_client, mock_vm):
    """vrg vm list --status --filter should combine filters."""
    mock_client.vms.list.return_value = [mock_vm]

    result = cli_runner.invoke(
        app, ["vm", "list", "--status", "running", "--filter", "name eq 'web'"]
    )

    assert result.exit_code == 0
    call_args = mock_client.vms.list.call_args
    assert "status eq 'running'" in call_args[1]["filter"]
    assert "name eq 'web'" in call_args[1]["filter"]


def test_vm_create_inline(cli_runner, mock_client, mock_vm):
    """vrg vm create --name should create VM inline."""
    mock_client.vms.create.return_value = mock_vm

    result = cli_runner.invoke(
        app,
        ["vm", "create", "--name", "new-vm", "--ram", "4096", "--cpu", "4"],
    )

    assert result.exit_code == 0
    assert "Created" in result.output
    mock_client.vms.create.assert_called_once_with(
        name="new-vm",
        ram=4096,
        cpu_cores=4,
        description="",
        os_family="linux",
    )


def test_vm_create_inline_no_name_fails(cli_runner, mock_client):
    """vrg vm create without --name or --file should fail."""
    result = cli_runner.invoke(app, ["vm", "create"])

    assert result.exit_code == 2


def test_vm_create_with_description(cli_runner, mock_client, mock_vm):
    """vrg vm create with --description should pass it through."""
    mock_client.vms.create.return_value = mock_vm

    result = cli_runner.invoke(
        app,
        ["vm", "create", "--name", "new-vm", "--description", "My VM", "--os", "windows"],
    )

    assert result.exit_code == 0
    mock_client.vms.create.assert_called_once_with(
        name="new-vm",
        ram=1024,
        cpu_cores=1,
        description="My VM",
        os_family="windows",
    )


def test_vm_get(cli_runner, mock_client, mock_vm):
    """vrg vm get should get VM details."""
    mock_client.vms.list.return_value = [mock_vm]
    mock_client.vms.get.return_value = mock_vm

    result = cli_runner.invoke(app, ["vm", "get", "test-vm"])

    assert result.exit_code == 0
    assert "test-vm" in result.output


def test_vm_update(cli_runner, mock_client, mock_vm):
    """vrg vm update should update VM fields."""
    mock_client.vms.list.return_value = [mock_vm]
    mock_client.vms.update.return_value = mock_vm

    result = cli_runner.invoke(
        app, ["vm", "update", "test-vm", "--name", "renamed-vm", "--ram", "8192"]
    )

    assert result.exit_code == 0
    mock_client.vms.update.assert_called_once_with(1, name="renamed-vm", ram=8192)


def test_vm_update_no_changes_fails(cli_runner, mock_client, mock_vm):
    """vrg vm update with no options should exit with error."""
    mock_client.vms.list.return_value = [mock_vm]

    result = cli_runner.invoke(app, ["vm", "update", "test-vm"])

    assert result.exit_code == 2


def test_vm_update_cpu_only(cli_runner, mock_client, mock_vm):
    """vrg vm update --cpu should only update CPU."""
    mock_client.vms.list.return_value = [mock_vm]
    mock_client.vms.update.return_value = mock_vm

    result = cli_runner.invoke(app, ["vm", "update", "test-vm", "--cpu", "8"])

    assert result.exit_code == 0
    mock_client.vms.update.assert_called_once_with(1, cpu_cores=8)


def test_vm_delete_with_yes(cli_runner, mock_client, mock_vm):
    """vrg vm delete --yes should delete without prompt."""
    mock_vm.is_running = False
    mock_client.vms.list.return_value = [mock_vm]
    mock_client.vms.get.return_value = mock_vm

    result = cli_runner.invoke(app, ["vm", "delete", "test-vm", "--yes"])

    assert result.exit_code == 0
    assert "Deleted" in result.output
    mock_client.vms.delete.assert_called_once_with(1)


def test_vm_delete_running_without_force_fails(cli_runner, mock_client, mock_vm):
    """vrg vm delete on running VM without --force should fail."""
    mock_vm.is_running = True
    mock_client.vms.list.return_value = [mock_vm]
    mock_client.vms.get.return_value = mock_vm

    result = cli_runner.invoke(app, ["vm", "delete", "test-vm", "--yes"])

    assert result.exit_code == 7
    mock_client.vms.delete.assert_not_called()


def test_vm_delete_running_with_force(cli_runner, mock_client, mock_vm):
    """vrg vm delete --force --yes powers off a running VM before deleting."""
    mock_vm.is_running = True
    mock_client.vms.list.return_value = [mock_vm]
    mock_client.vms.get.return_value = mock_vm

    with patch("verge_cli.commands.vm.wait_for_state", return_value=mock_vm) as wait_for_state:
        result = cli_runner.invoke(app, ["vm", "delete", "test-vm", "--force", "--yes"])

    assert result.exit_code == 0
    mock_vm.power_off.assert_called_once_with(force=True)
    wait_for_state.assert_called_once_with(
        get_resource=mock_client.vms.get,
        resource_key=1,
        target_state=["stopped", "offline"],
        state_field="status",
        resource_type="VM",
        quiet=False,
    )
    mock_client.vms.delete.assert_called_once_with(1)


def test_vm_start(cli_runner, mock_client, mock_vm):
    """vrg vm start should start a stopped VM."""
    mock_vm.is_running = False
    mock_client.vms.list.return_value = [mock_vm]
    mock_client.vms.get.return_value = mock_vm

    result = cli_runner.invoke(app, ["vm", "start", "test-vm"])

    assert result.exit_code == 0
    mock_vm.power_on.assert_called_once()


def test_vm_start_already_running(cli_runner, mock_client, mock_vm):
    """vrg vm start on running VM should show message."""
    mock_vm.is_running = True
    mock_client.vms.list.return_value = [mock_vm]
    mock_client.vms.get.return_value = mock_vm

    result = cli_runner.invoke(app, ["vm", "start", "test-vm"])

    assert result.exit_code == 0
    assert "already running" in result.output
    mock_vm.power_on.assert_not_called()


def test_vm_stop(cli_runner, mock_client, mock_vm):
    """vrg vm stop should stop a running VM."""
    mock_vm.is_running = True
    mock_client.vms.list.return_value = [mock_vm]
    mock_client.vms.get.return_value = mock_vm

    result = cli_runner.invoke(app, ["vm", "stop", "test-vm"])

    assert result.exit_code == 0
    mock_vm.power_off.assert_called_once_with(force=False)


def test_vm_stop_not_running(cli_runner, mock_client, mock_vm):
    """vrg vm stop on stopped VM should show message."""
    mock_vm.is_running = False
    mock_client.vms.list.return_value = [mock_vm]
    mock_client.vms.get.return_value = mock_vm

    result = cli_runner.invoke(app, ["vm", "stop", "test-vm"])

    assert result.exit_code == 0
    assert "not running" in result.output
    mock_vm.power_off.assert_not_called()


def test_vm_stop_force(cli_runner, mock_client, mock_vm):
    """vrg vm stop --force should force power off."""
    mock_vm.is_running = True
    mock_client.vms.list.return_value = [mock_vm]
    mock_client.vms.get.return_value = mock_vm

    result = cli_runner.invoke(app, ["vm", "stop", "test-vm", "--force"])

    assert result.exit_code == 0
    mock_vm.power_off.assert_called_once_with(force=True)


def test_vm_restart_running(cli_runner, mock_client, mock_vm):
    """vrg vm restart should stop then start a running VM."""
    mock_vm.is_running = True
    mock_client.vms.list.return_value = [mock_vm]
    mock_client.vms.get.return_value = mock_vm

    # After stop, vm should be in stopped state for the wait
    stopped_vm = MagicMock()
    stopped_vm.name = "test-vm"
    stopped_vm.is_running = False
    stopped_vm.get = lambda k, d=None: {"status": "stopped"}.get(k, d)

    with patch("verge_cli.commands.vm.wait_for_state", return_value=stopped_vm):
        result = cli_runner.invoke(app, ["vm", "restart", "test-vm"])

    assert result.exit_code == 0
    mock_vm.power_off.assert_called_once_with(force=False)
    stopped_vm.power_on.assert_called_once()


def test_vm_restart_not_running_fails(cli_runner, mock_client, mock_vm):
    """vrg vm restart on stopped VM should fail."""
    mock_vm.is_running = False
    mock_client.vms.list.return_value = [mock_vm]
    mock_client.vms.get.return_value = mock_vm

    result = cli_runner.invoke(app, ["vm", "restart", "test-vm"])

    assert result.exit_code == 1
    assert "not running" in result.output
