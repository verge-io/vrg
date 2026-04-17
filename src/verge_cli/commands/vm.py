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
    """List virtual machines.

    Returns every VM visible to the current session. Use `--status` to filter
    by lifecycle state (`running`, `stopped`, `error`, ...) or `--filter` to
    pass an arbitrary OData expression. Combine with `-A` to list across every
    configured profile.

    **Examples:**

        vrg vm list
        vrg vm list --status running
        vrg vm list --filter "cpu_cores gt 4"
        vrg -o json vm list | jq '.[] | select(.running)'
        vrg -A vm list
    """
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
    """Get details for a single virtual machine.

    Accepts a VM name or numeric key. Use `-o json` or `-o wide` for the full
    attribute set; the default table view shows the columns documented in
    `vrg vm list --help`.

    **Examples:**

        vrg vm get web-01
        vrg vm get 42
        vrg -o json vm get web-01
        vrg -o json -q '.status,.node_name' vm get web-01
    """
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
    """Create a new virtual machine, inline or from a `.vrg.yaml` template.

    Inline creation takes flags (`--name`, `--ram`, `--cpu`, ...) and produces
    a minimal VM with no drives or NICs — attach those afterwards with
    `vrg vm drive create` / `vrg vm nic create`. Template-based creation
    provisions drives, NICs, and devices in one operation; `--set` overrides
    individual values and `--dry-run` prints the plan without touching the
    cluster.

    **Examples:**

        # Inline
        vrg vm create --name web-03 --ram 4096 --cpu 4
        vrg vm create --name dev-01 --ram 2048 --cpu 2 --os linux

        # From template
        vrg vm create -f web-server.vrg.yaml
        vrg vm create -f web-server.vrg.yaml --set name=web-03 --set ram=8192
        vrg vm create -f web-server.vrg.yaml --dry-run
    """
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
    """Update a virtual machine's basic attributes.

    Only the flags you supply are changed; everything else stays as-is.
    CPU and RAM changes typically require a VM restart to take effect — check
    `needs_restart` on the returned object.

    **Examples:**

        vrg vm update web-01 --ram 8192
        vrg vm update web-01 --cpu 8 --ram 16384
        vrg vm update web-01 --name web-01-renamed
        vrg vm update 42 --description "Production web frontend"
    """
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
    """Delete a virtual machine.

    Prompts for confirmation unless `--yes` is passed. Running VMs are
    refused (exit 7) unless `--force` is also given, which powers the VM off
    before deletion. Deletion removes the VM and all its drives — snapshots
    on shared storage may still be retained per snapshot-profile policy.

    **Examples:**

        vrg vm delete web-01
        vrg vm delete web-01 --yes
        vrg vm delete web-01 --force --yes
    """
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
    """Power on a virtual machine.

    Returns as soon as the start request is accepted. Use `--wait` to block
    until the VM reaches the `running` state (or `--timeout` seconds elapse,
    defaulting to 300). If the VM is already running, the command is a no-op.

    **Examples:**

        vrg vm start web-01
        vrg vm start web-01 --wait
        vrg vm start web-01 --wait --timeout 60
    """
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
    """Stop a virtual machine.

    Issues an ACPI shutdown by default so the guest OS can shut down cleanly.
    Pass `--force` to power off immediately without guest cooperation (the
    equivalent of pulling the power cord). Use `--wait` to block until the
    VM reaches `stopped` / `offline`.

    **Examples:**

        vrg vm stop web-01
        vrg vm stop web-01 --wait
        vrg vm stop web-01 --force
        vrg vm stop web-01 --force --wait --timeout 60
    """
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

    Performs an ACPI shutdown, waits for the VM to reach `stopped`, then
    powers it back on. For a hard reset (equivalent to pressing the physical
    reset button), use `vrg vm reset` instead. `--timeout` is split evenly
    across the stop and start phases.

    **Examples:**

        vrg vm restart web-01
        vrg vm restart web-01 --wait
        vrg vm restart web-01 --wait --timeout 600
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
    """Hard-reset a virtual machine (equivalent to pressing the reset button).

    Unlike `vrg vm restart`, no ACPI shutdown is attempted — the guest OS
    receives no warning. Prefer `restart` whenever possible; use `reset` only
    when the guest is unresponsive. Prompts for confirmation unless `--yes`.

    **Examples:**

        vrg vm reset web-01
        vrg vm reset web-01 --yes
    """
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
    """Validate a `.vrg.yaml` template without creating any resources.

    Loads the template, applies `--set` overrides, and runs schema validation
    only — no API calls are made. Use this in CI to catch syntax, schema, and
    variable-substitution errors before invoking `vrg vm create -f`. Exits 8
    on validation failure.

    **Examples:**

        vrg vm validate -f web-server.vrg.yaml
        vrg vm validate -f web-server.vrg.yaml --set name=web-03
    """
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
    """Clone a virtual machine, including its drives and NIC configuration.

    A clone is a full copy — the new VM has independent drives based on the
    source's current contents. By default, NIC MAC addresses are regenerated
    to avoid conflicts on the same network; pass `--preserve-macs` to keep
    them (useful when replacing a VM on the same IP). The source VM can be
    running; the clone starts powered off.

    **Examples:**

        vrg vm clone web-01 --name web-01-copy
        vrg vm clone web-01 --name web-02 --preserve-macs
    """
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
    """Live-migrate a running virtual machine to another node.

    The VM keeps running throughout — its memory state is streamed to the
    target node, then execution switches over with no guest-visible
    downtime. Without `--node`, the scheduler picks a target. The VM must
    be in the `running` state; stopped VMs cannot be migrated.

    **Examples:**

        vrg vm migrate web-01
        vrg vm migrate web-01 --node node-2
        vrg vm migrate 42 --node 3
    """
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
    """Hibernate a virtual machine (save memory to disk, then power off).

    The VM's RAM is written to a hibernation file and the VM is powered off.
    A subsequent `vrg vm start` resumes execution from the saved state rather
    than booting the guest. Useful for freeing node resources without losing
    in-memory work. The VM must be running.

    **Examples:**

        vrg vm hibernate web-01
        vrg vm hibernate 42
    """
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
    """Attach a tag to a virtual machine.

    Tags are free-form labels managed under `vrg tag` and grouped by
    `vrg tag-category`. A VM may carry multiple tags; use them for
    environment, owner, role, or policy selectors.

    **Examples:**

        vrg vm tag web-01 production
        vrg vm tag web-01 env:prod
        vrg vm tag 42 owner:team-a
    """
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
    """Remove a tag from a virtual machine.

    Silently does nothing if the tag is not attached. The tag itself is not
    deleted — use `vrg tag delete` for that.

    **Examples:**

        vrg vm untag web-01 production
        vrg vm untag 42 env:prod
    """
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
    """Mark a virtual machine as a favorite for the current user.

    Favorites are a per-user UI convenience and appear pinned in the VergeOS
    web console. They have no effect on scheduling, permissions, or policy.

    **Examples:**

        vrg vm favorite web-01
        vrg vm favorite 42
    """
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
    """Remove a virtual machine from the current user's favorites.

    **Examples:**

        vrg vm unfavorite web-01
        vrg vm unfavorite 42
    """
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
    """Get VNC console connection info for a virtual machine.

    Returns the host, port, and one-time password needed to open a VNC
    session against the VM's framebuffer. The VM must be running. The
    credentials are single-use and short-lived — treat the output as a
    secret and connect promptly.

    **Examples:**

        vrg vm console web-01
        vrg -o json vm console web-01
    """
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
