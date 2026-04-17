"""VM commands for Verge CLI."""

from __future__ import annotations

from typing import Annotated, Any

import typer

from verge_cli.columns import VM_COLUMNS
from verge_cli.commands import vm_device, vm_drive, vm_export, vm_import, vm_nic, vm_snapshot
from verge_cli.context import get_context
from verge_cli.errors import handle_errors
from verge_cli.multi import list_all_profiles
from verge_cli.output import output_result, output_success
from verge_cli.utils import confirm_action, resolve_resource_id, wait_for_state

app = typer.Typer(
    name="vm",
    help=(
        "Manage virtual machines (VMs) on VergeOS.\n\n"
        "A VergeOS VM is a KVM-based virtual machine managed by the VergeHV"
        " hypervisor. VMs have **drives** (virtual disks on vSAN tiers),"
        " **NICs** (attached to virtual networks), and optional **devices**"
        " (e.g., TPM). They support live migration between nodes, snapshots,"
        " cloning, hibernation, and template-based creation from `.vrg.yaml`"
        " files.\n\n"
        "VMs are identified by **name** or **numeric key** in every command"
        " that accepts a VM argument. Use `vrg vm list` to see available VMs"
        " with their keys.\n\n"
        "Subresources have their own groups: `vrg vm drive`, `vrg vm nic`,"
        " `vrg vm device`, `vrg vm snapshot`, `vrg vm export`, and"
        " `vrg vm import`.\n\n"
        "---\n\n"
        "**Examples:**\n\n"
        "    # List all VMs\n"
        "    vrg vm list\n\n"
        "    # List only running VMs\n"
        "    vrg vm list --status running\n\n"
        "    # Get VM details as JSON\n"
        "    vrg -o json vm get web-01\n\n"
        "    # Create a VM inline\n"
        "    vrg vm create --name web-03 --ram 4096 --cpu 4\n\n"
        "    # Create from a template\n"
        "    vrg vm create -f web-server.vrg.yaml --set name=web-03\n\n"
        "    # Validate a template without creating\n"
        "    vrg vm validate -f web-server.vrg.yaml\n\n"
        "    # Lifecycle operations\n"
        "    vrg vm start web-01\n"
        "    vrg vm stop web-01\n"
        "    vrg vm restart web-01\n\n"
        "    # Live-migrate to another node\n"
        "    vrg vm migrate web-01 --node node-2\n\n"
        "    # Clone a VM\n"
        "    vrg vm clone web-01 --name web-01-copy\n\n"
        "    # Manage drives and NICs\n"
        "    vrg vm drive list web-01\n"
        "    vrg vm drive create web-01 --size 50GB --tier 2\n"
        "    vrg vm nic create web-01 --network internal-net\n\n"
        "    # Take a snapshot\n"
        "    vrg vm snapshot create web-01 --name before-upgrade\n\n"
        "---\n\n"
        "**Notes:**\n\n"
        "VMs are referenced by name or numeric key (`$key`). When a name"
        " matches multiple VMs, vrg prints all matches and exits with code 7."
        " Use the numeric key to disambiguate.\n\n"
        "`restart` performs a graceful shutdown followed by power-on. Use"
        " `reset` for a hard reset (equivalent to the physical reset button)."
        " `stop` requests an ACPI shutdown; add `--force` to power off"
        " immediately without guest cooperation.\n\n"
        "Templates (`.vrg.yaml`) support variable substitution with `--set`"
        " and batch creation. Use `--dry-run` with `vrg vm create -f` to"
        " preview resources without applying them. See `vrg vm validate` for"
        " schema-only checks."
    ),
    no_args_is_help=True,
    rich_markup_mode="markdown",
)

app.add_typer(vm_device.app, name="device")
app.add_typer(vm_drive.app, name="drive")
app.add_typer(vm_export.app, name="export")
app.add_typer(vm_import.app, name="import")
app.add_typer(vm_nic.app, name="nic")
app.add_typer(vm_snapshot.app, name="snapshot")


@app.command("list")
@handle_errors()
def vm_list(
    ctx: typer.Context,
    status: Annotated[
        str | None,
        typer.Option("--status", "-s", help="Filter by status (running, stopped, etc.)"),
    ] = None,
    filter: Annotated[
        str | None,
        typer.Option("--filter", help="OData filter expression (e.g., \"name eq 'foo'\")"),
    ] = None,
) -> None:
    """List virtual machines."""
    if ctx.obj.get("all_profiles"):
        list_all_profiles(ctx, lambda c: c.vms.list(), _vm_to_dict, VM_COLUMNS)
        return
    vctx = get_context(ctx)

    # Build filter
    odata_filter = filter
    if status:
        status_filter = f"status eq '{status}'"
        odata_filter = f"({odata_filter}) and {status_filter}" if odata_filter else status_filter

    vms = vctx.client.vms.list(filter=odata_filter)

    # Convert to dicts for output
    data = [_vm_to_dict(vm) for vm in vms]

    output_result(
        data,
        output_format=vctx.output_format,
        query=vctx.query,
        columns=VM_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("get")
@handle_errors()
def vm_get(
    ctx: typer.Context,
    vm: Annotated[str, typer.Argument(help="VM name or key")],
) -> None:
    """Get details of a virtual machine."""
    vctx = get_context(ctx)

    key = resolve_resource_id(vctx.client.vms, vm, "VM")
    vm_obj = vctx.client.vms.get(key)

    output_result(
        _vm_to_dict(vm_obj),
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("create")
@handle_errors()
def vm_create(
    ctx: typer.Context,
    name: Annotated[str | None, typer.Option("--name", "-n", help="VM name")] = None,
    ram: Annotated[int, typer.Option("--ram", "-r", help="RAM in MB")] = 1024,
    cpu: Annotated[int, typer.Option("--cpu", "-c", help="Number of CPU cores")] = 1,
    description: Annotated[str, typer.Option("--description", "-d", help="VM description")] = "",
    os_family: Annotated[
        str,
        typer.Option("--os", help="OS family (linux, windows, freebsd, other)"),
    ] = "linux",
    file: Annotated[
        str | None, typer.Option("--file", "-f", help="Template file (.vrg.yaml)")
    ] = None,
    set_overrides: Annotated[
        list[str] | None, typer.Option("--set", help="Override template values")
    ] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Show plan without creating")] = False,
) -> None:
    """Create a new virtual machine (inline or from template)."""
    if file:
        _create_from_template(ctx, file, set_overrides or [], dry_run)
    else:
        if not name:
            typer.echo("Error: --name is required for inline creation.", err=True)
            raise typer.Exit(2)
        _create_inline(ctx, name, ram, cpu, description, os_family)


def _create_inline(
    ctx: typer.Context,
    name: str,
    ram: int,
    cpu: int,
    description: str,
    os_family: str,
) -> None:
    """Original inline VM creation."""
    vctx = get_context(ctx)
    vm_obj = vctx.client.vms.create(
        name=name,
        ram=ram,
        cpu_cores=cpu,
        description=description,
        os_family=os_family,
    )

    output_success(f"Created VM '{vm_obj.name}' (key: {vm_obj.key})", quiet=vctx.quiet)

    output_result(
        _vm_to_dict(vm_obj),
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


def _create_from_template(
    ctx: typer.Context,
    file_path: str,
    set_overrides: list[str],
    dry_run: bool,
) -> None:
    """Template-based VM creation."""
    from verge_cli.template.builder import ProvisionError, build_dry_run, provision_vm
    from verge_cli.template.loader import load_template
    from verge_cli.template.schema import (
        ValidationError,
        convert_units,
        merge_vm_set_defaults,
        validate_template,
    )

    # Load and validate
    try:
        data = load_template(file_path, set_overrides=set_overrides)
        validate_template(data)
    except (ValueError, ValidationError) as e:
        typer.echo(f"Template error: {e}", err=True)
        raise typer.Exit(8) from None

    # Collect VM configs
    if data["kind"] == "VirtualMachineSet":
        defaults = data.get("defaults", {})
        vm_configs = merge_vm_set_defaults(defaults, data["vms"])
    else:
        vm_configs = [data["vm"]]

    # Convert units for all configs
    for vm_config in vm_configs:
        convert_units(vm_config)

    # Dry run
    if dry_run:
        typer.echo("Dry run — no resources will be created.\n")
        for vm_config in vm_configs:
            typer.echo(build_dry_run(vm_config))
            typer.echo("")
        return

    # Provision
    vctx = get_context(ctx)
    results = []
    had_errors = False

    for vm_config in vm_configs:
        try:
            result = provision_vm(vctx.client, vm_config)
            results.append(result)
            output_success(
                f"Created VM '{result.vm_name}' (key: {result.vm_key}) — "
                f"{result.drives_created} drives, {result.nics_created} NICs, "
                f"{result.devices_created} devices",
                quiet=vctx.quiet,
            )
        except ProvisionError as e:
            results.append(e.result)
            had_errors = True
            typer.echo(f"Warning: {e}", err=True)

    if had_errors:
        raise typer.Exit(1)


@app.command("update")
@handle_errors()
def vm_update(
    ctx: typer.Context,
    vm: Annotated[str, typer.Argument(help="VM name or key")],
    name: Annotated[str | None, typer.Option("--name", "-n", help="New VM name")] = None,
    ram: Annotated[int | None, typer.Option("--ram", "-r", help="RAM in MB")] = None,
    cpu: Annotated[int | None, typer.Option("--cpu", "-c", help="Number of CPU cores")] = None,
    description: Annotated[
        str | None,
        typer.Option("--description", "-d", help="VM description"),
    ] = None,
) -> None:
    """Update a virtual machine."""
    vctx = get_context(ctx)

    key = resolve_resource_id(vctx.client.vms, vm, "VM")

    # Build update kwargs (only non-None values)
    updates: dict[str, Any] = {}
    if name is not None:
        updates["name"] = name
    if ram is not None:
        updates["ram"] = ram
    if cpu is not None:
        updates["cpu_cores"] = cpu
    if description is not None:
        updates["description"] = description

    if not updates:
        typer.echo("No updates specified.", err=True)
        raise typer.Exit(2)

    vm_obj = vctx.client.vms.update(key, **updates)

    output_success(f"Updated VM '{vm_obj.name}'", quiet=vctx.quiet)

    output_result(
        _vm_to_dict(vm_obj),
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("delete")
@handle_errors()
def vm_delete(
    ctx: typer.Context,
    vm: Annotated[str, typer.Argument(help="VM name or key")],
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation")] = False,
    force: Annotated[bool, typer.Option("--force", "-f", help="Force delete running VM")] = False,
) -> None:
    """Delete a virtual machine."""
    vctx = get_context(ctx)

    key = resolve_resource_id(vctx.client.vms, vm, "VM")
    vm_obj = vctx.client.vms.get(key)

    # Check if running and not forcing
    if vm_obj.is_running and not force:
        typer.echo(f"Error: VM '{vm_obj.name}' is running. Use --force to delete anyway.", err=True)
        raise typer.Exit(7)

    if not confirm_action(f"Delete VM '{vm_obj.name}'?", yes=yes):
        typer.echo("Cancelled.")
        raise typer.Exit(0)

    vctx.client.vms.delete(key)
    output_success(f"Deleted VM '{vm_obj.name}'", quiet=vctx.quiet)


@app.command("start")
@handle_errors()
def vm_start(
    ctx: typer.Context,
    vm: Annotated[str, typer.Argument(help="VM name or key")],
    wait: Annotated[bool, typer.Option("--wait", "-w", help="Wait for VM to start")] = False,
    timeout: Annotated[int, typer.Option("--timeout", help="Wait timeout in seconds")] = 300,
) -> None:
    """Start a virtual machine."""
    vctx = get_context(ctx)

    key = resolve_resource_id(vctx.client.vms, vm, "VM")
    vm_obj = vctx.client.vms.get(key)

    if vm_obj.is_running:
        typer.echo(f"VM '{vm_obj.name}' is already running.")
        return

    vm_obj.power_on()
    output_success(f"Starting VM '{vm_obj.name}'", quiet=vctx.quiet)

    if wait:
        vm_obj = wait_for_state(
            get_resource=vctx.client.vms.get,
            resource_key=key,
            target_state="running",
            timeout=timeout,
            state_field="status",
            resource_type="VM",
            quiet=vctx.quiet,
        )
        output_success(f"VM '{vm_obj.name}' is now running", quiet=vctx.quiet)


@app.command("stop")
@handle_errors()
def vm_stop(
    ctx: typer.Context,
    vm: Annotated[str, typer.Argument(help="VM name or key")],
    force: Annotated[bool, typer.Option("--force", "-f", help="Force power off")] = False,
    wait: Annotated[bool, typer.Option("--wait", "-w", help="Wait for VM to stop")] = False,
    timeout: Annotated[int, typer.Option("--timeout", help="Wait timeout in seconds")] = 300,
) -> None:
    """Stop a virtual machine."""
    vctx = get_context(ctx)

    key = resolve_resource_id(vctx.client.vms, vm, "VM")
    vm_obj = vctx.client.vms.get(key)

    if not vm_obj.is_running:
        typer.echo(f"VM '{vm_obj.name}' is not running.")
        return

    vm_obj.power_off(force=force)
    action = "Forcing power off" if force else "Stopping"
    output_success(f"{action} VM '{vm_obj.name}'", quiet=vctx.quiet)

    if wait:
        vm_obj = wait_for_state(
            get_resource=vctx.client.vms.get,
            resource_key=key,
            target_state=["stopped", "offline"],
            timeout=timeout,
            state_field="status",
            resource_type="VM",
            quiet=vctx.quiet,
        )
        output_success(f"VM '{vm_obj.name}' is now stopped", quiet=vctx.quiet)


@app.command("restart")
@handle_errors()
def vm_restart(
    ctx: typer.Context,
    vm: Annotated[str, typer.Argument(help="VM name or key")],
    wait: Annotated[bool, typer.Option("--wait", "-w", help="Wait for VM to restart")] = False,
    timeout: Annotated[int, typer.Option("--timeout", help="Wait timeout in seconds")] = 300,
) -> None:
    """Restart a virtual machine (graceful stop then start).

    This performs a graceful shutdown followed by power on. For a hard reset
    (like pressing the reset button), use 'vrg vm reset' instead.
    """
    vctx = get_context(ctx)

    key = resolve_resource_id(vctx.client.vms, vm, "VM")
    vm_obj = vctx.client.vms.get(key)

    if not vm_obj.is_running:
        typer.echo(f"VM '{vm_obj.name}' is not running. Use 'vrg vm start' instead.")
        raise typer.Exit(1)

    # Graceful stop
    vm_obj.power_off(force=False)
    output_success(f"Stopping VM '{vm_obj.name}'...", quiet=vctx.quiet)

    # Wait for stop
    vm_obj = wait_for_state(
        get_resource=vctx.client.vms.get,
        resource_key=key,
        target_state=["stopped", "offline"],
        timeout=timeout // 2,  # Use half timeout for stop
        state_field="status",
        resource_type="VM",
        quiet=True,
    )

    # Start
    vm_obj.power_on()
    output_success(f"Starting VM '{vm_obj.name}'...", quiet=vctx.quiet)

    if wait:
        vm_obj = wait_for_state(
            get_resource=vctx.client.vms.get,
            resource_key=key,
            target_state="running",
            timeout=timeout // 2,
            state_field="status",
            resource_type="VM",
            quiet=vctx.quiet,
        )
        output_success(f"VM '{vm_obj.name}' has restarted", quiet=vctx.quiet)


@app.command("reset")
@handle_errors()
def vm_reset(
    ctx: typer.Context,
    vm: Annotated[str, typer.Argument(help="VM name or key")],
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation")] = False,
) -> None:
    """Hard reset a virtual machine (like pressing the reset button)."""
    vctx = get_context(ctx)

    key = resolve_resource_id(vctx.client.vms, vm, "VM")
    vm_obj = vctx.client.vms.get(key)

    if not vm_obj.is_running:
        typer.echo(f"VM '{vm_obj.name}' is not running.")
        raise typer.Exit(1)

    if not confirm_action(
        f"Reset VM '{vm_obj.name}'? This will forcefully restart the VM.", yes=yes
    ):
        typer.echo("Cancelled.")
        raise typer.Exit(0)

    vm_obj.reset()
    output_success(f"Reset VM '{vm_obj.name}'", quiet=vctx.quiet)


@app.command("validate")
@handle_errors()
def vm_validate(
    ctx: typer.Context,
    file: Annotated[
        str,
        typer.Option("--file", "-f", help="Path to .vrg.yaml template file"),
    ],
    set_overrides: Annotated[
        list[str] | None,
        typer.Option("--set", help="Override template values (key.path=value)"),
    ] = None,
) -> None:
    """Validate a VM template file without creating anything."""
    from verge_cli.template.loader import load_template
    from verge_cli.template.schema import ValidationError, validate_template

    try:
        data = load_template(file, set_overrides=set_overrides or [])
        validate_template(data)
    except (ValueError, ValidationError) as e:
        typer.echo(f"Validation failed: {e}", err=True)
        raise typer.Exit(8) from None

    quiet = ctx.obj.get("quiet", False) if ctx.obj else False
    output_success(f"Template '{file}' is valid.", quiet=quiet)


@app.command("clone")
@handle_errors()
def vm_clone(
    ctx: typer.Context,
    vm: Annotated[str, typer.Argument(help="VM name or key")],
    name: Annotated[str, typer.Option("--name", "-n", help="Name for the cloned VM")] = "",
    preserve_macs: Annotated[
        bool, typer.Option("--preserve-macs", help="Preserve MAC addresses")
    ] = False,
) -> None:
    """Clone a virtual machine."""
    vctx = get_context(ctx)

    key = resolve_resource_id(vctx.client.vms, vm, "VM")
    vm_obj = vctx.client.vms.get(key)

    result = vm_obj.clone(name=name, preserve_macs=preserve_macs)

    output_success(f"Cloned VM '{vm_obj.name}'", quiet=vctx.quiet)

    output_result(
        result,
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("migrate")
@handle_errors()
def vm_migrate(
    ctx: typer.Context,
    vm: Annotated[str, typer.Argument(help="VM name or key")],
    node: Annotated[
        str | None,
        typer.Option("--node", help="Target node name or key"),
    ] = None,
) -> None:
    """Live migrate a virtual machine to another node."""
    vctx = get_context(ctx)

    key = resolve_resource_id(vctx.client.vms, vm, "VM")
    vm_obj = vctx.client.vms.get(key)

    if not vm_obj.is_running:
        typer.echo(f"Error: VM '{vm_obj.name}' is not running.", err=True)
        raise typer.Exit(1)

    preferred_node: int | None = None
    if node is not None:
        preferred_node = resolve_resource_id(vctx.client.nodes, node, "Node")

    vm_obj.migrate(preferred_node=preferred_node)
    output_success(f"Migrating VM '{vm_obj.name}'", quiet=vctx.quiet)


@app.command("hibernate")
@handle_errors()
def vm_hibernate(
    ctx: typer.Context,
    vm: Annotated[str, typer.Argument(help="VM name or key")],
) -> None:
    """Hibernate a virtual machine (save memory to disk and power off)."""
    vctx = get_context(ctx)

    key = resolve_resource_id(vctx.client.vms, vm, "VM")
    vm_obj = vctx.client.vms.get(key)

    if not vm_obj.is_running:
        typer.echo(f"Error: VM '{vm_obj.name}' is not running.", err=True)
        raise typer.Exit(1)

    vm_obj.hibernate()
    output_success(f"Hibernating VM '{vm_obj.name}'", quiet=vctx.quiet)


@app.command("tag")
@handle_errors()
def vm_tag(
    ctx: typer.Context,
    vm: Annotated[str, typer.Argument(help="VM name or key")],
    tag: Annotated[str, typer.Argument(help="Tag name or key")],
) -> None:
    """Add a tag to a virtual machine."""
    vctx = get_context(ctx)

    key = resolve_resource_id(vctx.client.vms, vm, "VM")
    vm_obj = vctx.client.vms.get(key)

    tag_key = resolve_resource_id(vctx.client.tags, tag, "Tag")

    vm_obj.tag(int(tag_key))
    output_success(f"Tagged VM '{vm_obj.name}' with tag '{tag}'", quiet=vctx.quiet)


@app.command("untag")
@handle_errors()
def vm_untag(
    ctx: typer.Context,
    vm: Annotated[str, typer.Argument(help="VM name or key")],
    tag: Annotated[str, typer.Argument(help="Tag name or key")],
) -> None:
    """Remove a tag from a virtual machine."""
    vctx = get_context(ctx)

    key = resolve_resource_id(vctx.client.vms, vm, "VM")
    vm_obj = vctx.client.vms.get(key)

    tag_key = resolve_resource_id(vctx.client.tags, tag, "Tag")

    vm_obj.untag(int(tag_key))
    output_success(f"Removed tag '{tag}' from VM '{vm_obj.name}'", quiet=vctx.quiet)


@app.command("favorite")
@handle_errors()
def vm_favorite(
    ctx: typer.Context,
    vm: Annotated[str, typer.Argument(help="VM name or key")],
) -> None:
    """Mark a virtual machine as a favorite."""
    vctx = get_context(ctx)

    key = resolve_resource_id(vctx.client.vms, vm, "VM")
    vm_obj = vctx.client.vms.get(key)

    vm_obj.favorite()
    output_success(f"Favorited VM '{vm_obj.name}'", quiet=vctx.quiet)


@app.command("unfavorite")
@handle_errors()
def vm_unfavorite(
    ctx: typer.Context,
    vm: Annotated[str, typer.Argument(help="VM name or key")],
) -> None:
    """Remove a virtual machine from favorites."""
    vctx = get_context(ctx)

    key = resolve_resource_id(vctx.client.vms, vm, "VM")
    vm_obj = vctx.client.vms.get(key)

    vm_obj.unfavorite()
    output_success(f"Unfavorited VM '{vm_obj.name}'", quiet=vctx.quiet)


@app.command("console")
@handle_errors()
def vm_console(
    ctx: typer.Context,
    vm: Annotated[str, typer.Argument(help="VM name or key")],
) -> None:
    """Get console connection info for a virtual machine."""
    vctx = get_context(ctx)

    key = resolve_resource_id(vctx.client.vms, vm, "VM")
    vm_obj = vctx.client.vms.get(key)

    info = vm_obj.get_console_info()

    output_result(
        info,
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


def _vm_to_dict(vm: Any) -> dict[str, Any]:
    """Convert a VM object to a dictionary for output."""
    return {
        "$key": vm.key,
        "name": vm.name,
        "description": vm.get("description", ""),
        "status": vm.status,
        "running": vm.is_running,
        "cpu_cores": vm.get("cpu_cores"),
        "ram": vm.get("ram"),
        "os_family": vm.get("os_family"),
        "cluster_name": vm.cluster_name,
        "node_name": vm.node_name,
        "created": vm.get("created"),
        "modified": vm.get("modified"),
        # Status flag for pending changes
        "needs_restart": vm.get("need_restart", False),
    }
