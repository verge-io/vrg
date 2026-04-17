"""Network IP alias commands for Verge CLI."""

from __future__ import annotations

from typing import Annotated, Any

import typer

from verge_cli.columns import ALIAS_COLUMNS
from verge_cli.context import get_context
from verge_cli.errors import ResourceNotFoundError, handle_errors
from verge_cli.output import output_result, output_success
from verge_cli.utils import confirm_action, resolve_resource_id

app = typer.Typer(
    name="alias",
    help=(
        "Manage per-network **rule aliases** — named IP address entries"
        " referenced by firewall, NAT, and routing rules.\n\n"
        "A network alias binds a **name** to an **IP address** (or CIDR"
        " block) inside a vnet so the same address can be reused across"
        " many rules without copy-pasting. In rule source/destination"
        " fields, refer to an alias as `alias:<name>` — change the alias"
        " once and every rule that references it picks up the new value on"
        " the next apply. Use aliases for addresses that change"
        " frequently (e.g. an admin jumphost IP) or that belong together"
        " as a logical set (e.g. `management-servers`, `monitoring`).\n\n"
        "Aliases are identified by **name (hostname)**, **IP address**,"
        " or **numeric key** within their network. Use `-o json` for"
        " machine-readable output; `--query` against the `hostname`, `ip`,"
        " and `description` fields.\n\n"
        "---\n\n"
        "**Examples:**\n\n"
        "    # List aliases on a network (JSON for agents)\n"
        "    vrg -o json network alias list internal-prod\n\n"
        "    # Get a specific alias by name, IP, or key\n"
        "    vrg network alias get internal-prod trusted-admin\n"
        "    vrg network alias get internal-prod 10.0.1.5\n\n"
        "    # Create an alias (name is what you use in rules as"
        " alias:<name>)\n"
        "    vrg network alias create internal-prod --name trusted-admin"
        " --ip 10.0.1.5 --description 'Ops jumphost'\n\n"
        "    # Reference the alias from a firewall rule\n"
        "    vrg network rule create internal-prod --name allow-ssh-admin"
        " --direction incoming --action accept --protocol tcp"
        " --dest-ports 22 --source-ip alias:trusted-admin\n\n"
        "    # Update an alias (replaces the entry — delete + recreate)\n"
        "    vrg network alias update internal-prod trusted-admin"
        " --ip 10.0.1.6\n\n"
        "    # Delete an alias (skip prompt with -y)\n"
        "    vrg network alias delete internal-prod trusted-admin -y\n\n"
        "---\n\n"
        "**Notes:**\n\n"
        "Changing an alias does **not** automatically reload the rules"
        " that reference it. After creating, updating, or deleting an"
        " alias, run `vrg network apply-rules <network>` on every"
        " network whose rules reference it so the new address takes"
        " effect in nftables.\n\n"
        "Because the underlying API does not expose a PUT for aliases,"
        " `alias update` is implemented as **delete + recreate**. The"
        " numeric key changes as a result; rules that reference the"
        " alias by `alias:<name>` are unaffected.\n\n"
        "Networks are identified by name or numeric key. Ambiguous"
        " network names return **exit code 7** (multiple matches);"
        " missing networks or aliases return **exit code 6** (not"
        " found)."
    ),
    no_args_is_help=True,
    rich_markup_mode="markdown",
)


def _resolve_alias_id(network: Any, identifier: str) -> int:
    """Resolve an alias name, IP, or ID to a key.

    Args:
        network: Network object with aliases collection.
        identifier: Alias hostname, IP address, or numeric key.

    Returns:
        The alias key.

    Raises:
        ResourceNotFoundError: If alias not found.
    """
    aliases = network.aliases.list()
    for alias in aliases:
        hostname = alias.get("hostname") or getattr(alias, "hostname", "")
        ip = alias.get("ip") or getattr(alias, "ip", "")
        key = alias.get("$key") or getattr(alias, "key", None)
        if (hostname == identifier or ip == identifier) and key is not None:
            return int(key)

    # If numeric, treat as key
    if identifier.isdigit():
        return int(identifier)

    raise ResourceNotFoundError(f"Alias '{identifier}' not found")


def _alias_to_dict(alias: Any) -> dict[str, Any]:
    """Convert a NetworkAlias object to a dictionary for output.

    Args:
        alias: Alias object from SDK.

    Returns:
        Dictionary representation of the alias.
    """
    return {
        "$key": alias.key,
        "ip": alias.get("ip", ""),
        "hostname": alias.get("hostname", ""),
        "description": alias.get("description", ""),
        "mac": alias.get("mac", ""),
    }


@app.command("list")
@handle_errors()
def alias_list(
    ctx: typer.Context,
    network: Annotated[str, typer.Argument(help="Network name or key")],
) -> None:
    """List IP aliases for a network."""
    vctx = get_context(ctx)

    net_key = resolve_resource_id(vctx.client.networks, network, "network")
    net_obj = vctx.client.networks.get(net_key)

    aliases = net_obj.aliases.list()
    data = [_alias_to_dict(alias) for alias in aliases]

    output_result(
        data,
        output_format=vctx.output_format,
        query=vctx.query,
        columns=ALIAS_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("get")
@handle_errors()
def alias_get(
    ctx: typer.Context,
    network: Annotated[str, typer.Argument(help="Network name or key")],
    alias: Annotated[str, typer.Argument(help="Alias name, IP, or key")],
) -> None:
    """Get details of an IP alias."""
    vctx = get_context(ctx)

    net_key = resolve_resource_id(vctx.client.networks, network, "network")
    net_obj = vctx.client.networks.get(net_key)

    alias_key = _resolve_alias_id(net_obj, alias)
    alias_obj = net_obj.aliases.get(alias_key)

    output_result(
        _alias_to_dict(alias_obj),
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("create")
@handle_errors()
def alias_create(
    ctx: typer.Context,
    network: Annotated[str, typer.Argument(help="Network name or key")],
    ip: Annotated[str, typer.Option("--ip", "-i", help="IP address or CIDR")],
    name: Annotated[
        str, typer.Option("--name", "-n", help="Alias name (used as alias:name in rules)")
    ],
    description: Annotated[str, typer.Option("--description", "-d", help="Description")] = "",
) -> None:
    """Create a new IP alias."""
    vctx = get_context(ctx)

    net_key = resolve_resource_id(vctx.client.networks, network, "network")
    net_obj = vctx.client.networks.get(net_key)

    alias_obj = net_obj.aliases.create(ip=ip, name=name, description=description)

    output_success(f"Created alias '{alias_obj.hostname}' ({alias_obj.ip})", quiet=vctx.quiet)

    output_result(
        _alias_to_dict(alias_obj),
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("update")
@handle_errors()
def alias_update(
    ctx: typer.Context,
    network: Annotated[str, typer.Argument(help="Network name or key")],
    alias: Annotated[str, typer.Argument(help="Alias name, IP, or key")],
    ip: Annotated[str | None, typer.Option("--ip", "-i", help="New IP address")] = None,
    name: Annotated[str | None, typer.Option("--name", "-n", help="New alias name")] = None,
    description: Annotated[
        str | None, typer.Option("--description", "-d", help="New description")
    ] = None,
) -> None:
    """Update an IP alias (delete + create).

    Since the SDK doesn't expose PUT for aliases, this command
    deletes the existing alias and recreates it with the new values.
    """
    vctx = get_context(ctx)

    net_key = resolve_resource_id(vctx.client.networks, network, "network")
    net_obj = vctx.client.networks.get(net_key)

    alias_key = _resolve_alias_id(net_obj, alias)
    existing = net_obj.aliases.get(alias_key)

    # Check if any updates were specified
    if ip is None and name is None and description is None:
        typer.echo("No updates specified.", err=True)
        raise typer.Exit(2)

    # Merge updates with existing values
    new_ip = ip if ip is not None else existing.ip
    new_name = name if name is not None else (existing.hostname or "")
    new_desc = description if description is not None else (existing.get("description") or "")

    # Delete and recreate (SDK doesn't expose PUT for aliases)
    net_obj.aliases.delete(alias_key)
    alias_obj = net_obj.aliases.create(ip=new_ip, name=new_name, description=new_desc)

    output_success(f"Updated alias '{alias_obj.hostname}'", quiet=vctx.quiet)

    output_result(
        _alias_to_dict(alias_obj),
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("delete")
@handle_errors()
def alias_delete(
    ctx: typer.Context,
    network: Annotated[str, typer.Argument(help="Network name or key")],
    alias: Annotated[str, typer.Argument(help="Alias name, IP, or key")],
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation")] = False,
) -> None:
    """Delete an IP alias."""
    vctx = get_context(ctx)

    net_key = resolve_resource_id(vctx.client.networks, network, "network")
    net_obj = vctx.client.networks.get(net_key)

    alias_key = _resolve_alias_id(net_obj, alias)
    alias_obj = net_obj.aliases.get(alias_key)

    alias_name = alias_obj.hostname or alias_obj.ip

    if not confirm_action(f"Delete alias '{alias_name}'?", yes=yes):
        typer.echo("Cancelled.")
        raise typer.Exit(0)

    net_obj.aliases.delete(alias_key)
    output_success(f"Deleted alias '{alias_name}'", quiet=vctx.quiet)
