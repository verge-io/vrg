"""VM NIC sub-resource commands."""

from __future__ import annotations

from typing import Annotated, Any

import typer

from verge_cli.columns import NIC_COLUMNS
from verge_cli.context import get_context
from verge_cli.errors import ResourceNotFoundError, handle_errors
from verge_cli.output import output_result, output_success
from verge_cli.utils import confirm_action, resolve_resource_id

app = typer.Typer(
    name="nic",
    help=(
        "Manage network interfaces attached to a VM.\n\n"
        "Each NIC connects the VM to a VergeOS virtual network. NICs have an"
        " interface type (`virtio`, `e1000`, `rtl8139`), a MAC address"
        " (auto-generated or manual), and an optional static IP. NICs are"
        " addressed by **name** or **numeric key** within the parent VM.\n\n"
        "Use `-o json` for structured output. The first argument to every"
        " command is the parent VM (name or key).\n\n"
        "---\n\n"
        "**Examples:**\n\n"
        "    vrg vm nic list web-01\n\n"
        "    vrg -o json vm nic get web-01 nic-0\n\n"
        "    vrg vm nic create web-01 --network internal-net\n\n"
        "    vrg vm nic create web-01 --network dmz --ip 10.0.1.50\n\n"
        "    vrg vm nic update web-01 nic-0 --network external-net\n\n"
        "    vrg vm nic delete web-01 nic-0 --yes\n\n"
        "---\n\n"
        "**Notes:**\n\n"
        "The `--network` option accepts a network name or numeric key. When a"
        " name matches multiple networks, the command exits with code 7."
    ),
    no_args_is_help=True,
    rich_markup_mode="markdown",
)


def _get_vm(ctx: typer.Context, vm_identifier: str) -> tuple[Any, Any]:
    """Get the VergeContext and VM object."""
    vctx = get_context(ctx)
    key = resolve_resource_id(vctx.client.vms, vm_identifier, "VM")
    vm_obj = vctx.client.vms.get(key)
    return vctx, vm_obj


def _nic_to_dict(nic: Any) -> dict[str, Any]:
    """Convert a NIC object to a dict for output."""
    return {
        "$key": nic.key,
        "name": nic.name,
        "description": nic.get("description", ""),
        "interface": nic.get("interface", ""),
        "network_name": nic.network_name,
        "network_key": nic.network_key,
        "mac_address": nic.mac_address,
        "ip_address": nic.ip_address,
        "enabled": nic.is_enabled,
    }


def _resolve_nic(vm_obj: Any, identifier: str) -> int:
    """Resolve a NIC name or ID to a key."""
    if identifier.isdigit():
        return int(identifier)
    nics = vm_obj.nics.list()
    matches = [n for n in nics if n.name == identifier]
    if len(matches) == 1:
        return int(matches[0].key)
    if len(matches) > 1:
        typer.echo(f"Error: Multiple NICs match '{identifier}'. Use a numeric key.", err=True)
        raise typer.Exit(7)
    typer.echo(f"Error: NIC '{identifier}' not found.", err=True)
    raise typer.Exit(6)


@app.command("list")
@handle_errors()
def nic_list(
    ctx: typer.Context,
    vm: Annotated[str, typer.Argument(help="VM name or key")],
) -> None:
    """List network interfaces on a VM.

    **Examples:**

        vrg vm nic list web-01
        vrg -o json vm nic list web-01
    """
    vctx, vm_obj = _get_vm(ctx, vm)
    nics = vm_obj.nics.list()
    data = [_nic_to_dict(n) for n in nics]
    output_result(
        data,
        output_format=vctx.output_format,
        query=vctx.query,
        columns=NIC_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("get")
@handle_errors()
def nic_get(
    ctx: typer.Context,
    vm: Annotated[str, typer.Argument(help="VM name or key")],
    nic: Annotated[str, typer.Argument(help="NIC name or key")],
) -> None:
    """Get details of a VM network interface.

    **Examples:**

        vrg vm nic get web-01 nic-0
        vrg -o json vm nic get web-01 42
    """
    vctx, vm_obj = _get_vm(ctx, vm)
    nic_key = _resolve_nic(vm_obj, nic)
    nic_obj = vm_obj.nics.get(nic_key)
    output_result(
        _nic_to_dict(nic_obj),
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("create")
@handle_errors()
def nic_create(
    ctx: typer.Context,
    vm: Annotated[str, typer.Argument(help="VM name or key")],
    network: Annotated[str, typer.Option("--network", "-N", help="Network name or key")],
    name: Annotated[str | None, typer.Option("--name", "-n", help="NIC name")] = None,
    interface: Annotated[
        str, typer.Option("--interface", "-i", help="NIC interface type")
    ] = "virtio",
    mac: Annotated[str | None, typer.Option("--mac", help="MAC address")] = None,
    ip: Annotated[str | None, typer.Option("--ip", help="IP address")] = None,
    description: Annotated[str, typer.Option("--description", help="Description")] = "",
) -> None:
    """Add a network interface to a VM.

    The `--network` option accepts a network name or numeric key. MAC
    addresses are auto-generated unless `--mac` is specified.

    **Examples:**

        vrg vm nic create web-01 --network internal-net
        vrg vm nic create web-01 --network dmz --ip 10.0.1.50
        vrg vm nic create web-01 --network 42 --interface e1000
    """
    vctx, vm_obj = _get_vm(ctx, vm)

    # Pass network as-is — SDK resolves names internally
    try:
        nic_obj = vm_obj.nics.create(
            network=network,
            name=name,
            interface=interface,
            mac_address=mac,
            ip_address=ip,
            description=description,
        )
    except Exception as e:
        if "not found" in str(e).lower():
            raise ResourceNotFoundError(str(e)) from e
        raise

    output_success(f"Created NIC '{nic_obj.name}' (key: {nic_obj.key})", quiet=vctx.quiet)
    output_result(
        _nic_to_dict(nic_obj),
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("update")
@handle_errors()
def nic_update(
    ctx: typer.Context,
    vm: Annotated[str, typer.Argument(help="VM name or key")],
    nic: Annotated[str, typer.Argument(help="NIC name or key")],
    name: Annotated[str | None, typer.Option("--name", "-n", help="New name")] = None,
    network: Annotated[str | None, typer.Option("--network", "-N", help="New network")] = None,
    enabled: Annotated[bool | None, typer.Option("--enabled/--disabled")] = None,
) -> None:
    """Update a VM network interface.

    Only the flags you supply are changed.

    **Examples:**

        vrg vm nic update web-01 nic-0 --network external-net
        vrg vm nic update web-01 nic-0 --disabled
    """
    vctx, vm_obj = _get_vm(ctx, vm)
    nic_key = _resolve_nic(vm_obj, nic)

    updates: dict[str, Any] = {}
    if name is not None:
        updates["name"] = name
    if network is not None:
        updates["network"] = network
    if enabled is not None:
        updates["enabled"] = enabled

    if not updates:
        typer.echo("No updates specified.", err=True)
        raise typer.Exit(2)

    nic_obj = vm_obj.nics.update(nic_key, **updates)
    output_success(f"Updated NIC '{nic_obj.name}'", quiet=vctx.quiet)
    output_result(
        _nic_to_dict(nic_obj),
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("delete")
@handle_errors()
def nic_delete(
    ctx: typer.Context,
    vm: Annotated[str, typer.Argument(help="VM name or key")],
    nic: Annotated[str, typer.Argument(help="NIC name or key")],
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation")] = False,
) -> None:
    """Remove a network interface from a VM.

    Prompts for confirmation unless `--yes` is passed.

    **Examples:**

        vrg vm nic delete web-01 nic-0
        vrg vm nic delete web-01 nic-0 --yes
    """
    vctx, vm_obj = _get_vm(ctx, vm)
    nic_key = _resolve_nic(vm_obj, nic)

    if not confirm_action(f"Delete NIC '{nic}'?", yes=yes):
        typer.echo("Cancelled.")
        raise typer.Exit(0)

    vm_obj.nics.delete(nic_key)
    output_success(f"Deleted NIC '{nic}'", quiet=vctx.quiet)
