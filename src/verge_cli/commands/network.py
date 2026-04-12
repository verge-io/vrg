"""Network commands for Verge CLI."""

from __future__ import annotations

import ipaddress
from typing import Annotated, Any

import typer

from verge_cli.columns import NETWORK_COLUMNS
from verge_cli.commands import (
    network_alias,
    network_diag,
    network_dns,
    network_host,
    network_rule,
)
from verge_cli.context import get_context
from verge_cli.errors import handle_errors
from verge_cli.multi import list_all_profiles
from verge_cli.output import output_result, output_success
from verge_cli.utils import confirm_action, resolve_resource_id

app = typer.Typer(
    name="network",
    help="Manage virtual networks.",
    no_args_is_help=True,
)

# Register subapps
app.add_typer(network_alias.app, name="alias")
app.add_typer(network_diag.app, name="diag")
app.add_typer(network_dns.app, name="dns")
app.add_typer(network_host.app, name="host")
app.add_typer(network_rule.app, name="rule")


@app.command("list")
@handle_errors()
def network_list(
    ctx: typer.Context,
    network_type: Annotated[
        str | None,
        typer.Option("--type", "-t", help="Filter by network type"),
    ] = None,
    status: Annotated[
        str | None,
        typer.Option("--status", "-s", help="Filter by status"),
    ] = None,
    filter: Annotated[
        str | None,
        typer.Option("--filter", help="OData filter expression (e.g., \"name eq 'foo'\")"),
    ] = None,
) -> None:
    """List virtual networks."""
    if ctx.obj.get("all_profiles"):
        list_all_profiles(ctx, lambda c: c.networks.list(), _network_to_dict, NETWORK_COLUMNS)
        return
    vctx = get_context(ctx)

    # Build filter
    odata_filter = filter
    if network_type:
        type_filter = f"type eq '{network_type}'"
        odata_filter = f"({odata_filter}) and {type_filter}" if odata_filter else type_filter
    if status:
        status_filter = f"status eq '{status}'"
        odata_filter = f"({odata_filter}) and {status_filter}" if odata_filter else status_filter

    networks = vctx.client.networks.list(filter=odata_filter)

    # Convert to dicts for output
    data = [_network_to_dict(net) for net in networks]

    output_result(
        data,
        output_format=vctx.output_format,
        query=vctx.query,
        columns=NETWORK_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("get")
@handle_errors()
def network_get(
    ctx: typer.Context,
    network: Annotated[str, typer.Argument(help="Network name or key")],
) -> None:
    """Get details of a virtual network."""
    vctx = get_context(ctx)

    key = resolve_resource_id(vctx.client.networks, network, "network")
    net_obj = vctx.client.networks.get(key)

    output_result(
        _network_to_dict(net_obj),
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("create")
@handle_errors()
def network_create(
    ctx: typer.Context,
    name: Annotated[str, typer.Option("--name", "-n", help="Network name")],
    network_type: Annotated[
        str,
        typer.Option("--type", "-t", help="Network type (internal, external)"),
    ] = "internal",
    cidr: Annotated[
        str | None,
        typer.Option("--cidr", "-c", help="Network CIDR (e.g., 10.0.0.0/24)"),
    ] = None,
    ip_address: Annotated[
        str | None,
        typer.Option("--ip", "-i", help="Network interface IP address"),
    ] = None,
    gateway: Annotated[
        str | None,
        typer.Option("--gateway", "-g", help="Default gateway"),
    ] = None,
    description: Annotated[
        str,
        typer.Option("--description", "-d", help="Network description"),
    ] = "",
    dhcp: Annotated[
        bool,
        typer.Option("--dhcp/--no-dhcp", help="Enable DHCP server"),
    ] = False,
    dhcp_start: Annotated[
        str | None,
        typer.Option("--dhcp-start", help="DHCP range start IP"),
    ] = None,
    dhcp_stop: Annotated[
        str | None,
        typer.Option("--dhcp-stop", help="DHCP range end IP"),
    ] = None,
    vnet_default_gateway: Annotated[
        str | None,
        typer.Option(
            "--vnet-default-gateway",
            help="Route traffic through this network (name or key)",
        ),
    ] = None,
) -> None:
    """Create a new virtual network."""
    vctx = get_context(ctx)

    create_kwargs: dict[str, Any] = {
        "name": name,
        "network_type": network_type,
        "description": description,
    }

    if cidr:
        create_kwargs["network_address"] = cidr
        # API requires ipaddress alongside network CIDR — auto-derive if not provided
        if not ip_address:
            try:
                net = ipaddress.ip_network(cidr, strict=False)
                ip_address = str(list(net.hosts())[0])
            except (ValueError, StopIteration):
                pass
    if ip_address:
        create_kwargs["ip_address"] = ip_address
    if gateway:
        create_kwargs["gateway"] = gateway
    if dhcp:
        create_kwargs["dhcp_enabled"] = True
        if dhcp_start:
            create_kwargs["dhcp_start"] = dhcp_start
        if dhcp_stop:
            create_kwargs["dhcp_stop"] = dhcp_stop
    if vnet_default_gateway:
        gw_key = resolve_resource_id(vctx.client.networks, vnet_default_gateway, "network")
        create_kwargs["interface_network"] = gw_key

    net_obj = vctx.client.networks.create(**create_kwargs)

    output_success(f"Created network '{net_obj.name}' (key: {net_obj.key})", quiet=vctx.quiet)

    output_result(
        _network_to_dict(net_obj),
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("update")
@handle_errors()
def network_update(
    ctx: typer.Context,
    network: Annotated[str, typer.Argument(help="Network name or key")],
    name: Annotated[str | None, typer.Option("--name", "-n", help="New network name")] = None,
    description: Annotated[
        str | None,
        typer.Option("--description", "-d", help="Network description"),
    ] = None,
    gateway: Annotated[
        str | None,
        typer.Option("--gateway", "-g", help="Default gateway"),
    ] = None,
) -> None:
    """Update a virtual network."""
    vctx = get_context(ctx)

    key = resolve_resource_id(vctx.client.networks, network, "network")

    # Build update kwargs (only non-None values)
    updates: dict[str, Any] = {}
    if name is not None:
        updates["name"] = name
    if description is not None:
        updates["description"] = description
    if gateway is not None:
        updates["gateway"] = gateway

    if not updates:
        typer.echo("No updates specified.", err=True)
        raise typer.Exit(2)

    net_obj = vctx.client.networks.update(key, **updates)

    output_success(f"Updated network '{net_obj.name}'", quiet=vctx.quiet)

    output_result(
        _network_to_dict(net_obj),
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("delete")
@handle_errors()
def network_delete(
    ctx: typer.Context,
    network: Annotated[str, typer.Argument(help="Network name or key")],
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation")] = False,
) -> None:
    """Delete a virtual network."""
    vctx = get_context(ctx)

    key = resolve_resource_id(vctx.client.networks, network, "network")
    net_obj = vctx.client.networks.get(key)

    if not confirm_action(f"Delete network '{net_obj.name}'?", yes=yes):
        typer.echo("Cancelled.")
        raise typer.Exit(0)

    vctx.client.networks.delete(key)
    output_success(f"Deleted network '{net_obj.name}'", quiet=vctx.quiet)


@app.command("start")
@handle_errors()
def network_start(
    ctx: typer.Context,
    network: Annotated[str, typer.Argument(help="Network name or key")],
) -> None:
    """Start a virtual network."""
    vctx = get_context(ctx)

    key = resolve_resource_id(vctx.client.networks, network, "network")
    net_obj = vctx.client.networks.get(key)

    if net_obj.get("running"):
        typer.echo(f"Network '{net_obj.name}' is already running.")
        return

    net_obj.power_on()
    output_success(f"Started network '{net_obj.name}'", quiet=vctx.quiet)


@app.command("stop")
@handle_errors()
def network_stop(
    ctx: typer.Context,
    network: Annotated[str, typer.Argument(help="Network name or key")],
    force: Annotated[bool, typer.Option("--force", "-f", help="Force stop")] = False,
) -> None:
    """Stop a virtual network."""
    vctx = get_context(ctx)

    key = resolve_resource_id(vctx.client.networks, network, "network")
    net_obj = vctx.client.networks.get(key)

    if not net_obj.get("running"):
        typer.echo(f"Network '{net_obj.name}' is not running.")
        return

    net_obj.power_off(force=force)
    action = "Force stopped" if force else "Stopped"
    output_success(f"{action} network '{net_obj.name}'", quiet=vctx.quiet)


@app.command("restart")
@handle_errors()
def network_restart(
    ctx: typer.Context,
    network: Annotated[str, typer.Argument(help="Network name or key")],
    apply_rules: Annotated[
        bool,
        typer.Option("--apply-rules/--no-apply-rules", help="Apply firewall rules after restart"),
    ] = True,
    wait: Annotated[
        bool, typer.Option("--wait", "-w", help="Wait for network to be running")
    ] = False,
    timeout: Annotated[int, typer.Option("--timeout", "-t", help="Timeout in seconds")] = 300,
) -> None:
    """Restart a virtual network."""
    vctx = get_context(ctx)

    key = resolve_resource_id(vctx.client.networks, network, "network")
    net_obj = vctx.client.networks.get(key)

    net_obj.restart(apply_rules=apply_rules)
    output_success(f"Restarted network '{net_obj.name}'", quiet=vctx.quiet)

    if wait:
        from verge_cli.utils import wait_for_state

        net_obj = wait_for_state(
            vctx.client.networks.get,
            key,
            target_state="running",
            timeout=timeout,
            state_field="status",
            resource_type="network",
            quiet=vctx.quiet,
        )
        output_success(f"Network '{net_obj.name}' is now running", quiet=vctx.quiet)


@app.command("apply-rules")
@handle_errors()
def network_apply_rules(
    ctx: typer.Context,
    network: Annotated[str, typer.Argument(help="Network name or key")],
) -> None:
    """Apply pending firewall rules to a network."""
    vctx = get_context(ctx)

    key = resolve_resource_id(vctx.client.networks, network, "network")
    net_obj = vctx.client.networks.get(key)

    if not net_obj.get("running"):
        typer.echo(
            f"Network '{net_obj.name}' is not running. Rules can only be applied to running networks.",
            err=True,
        )
        raise typer.Exit(1)

    net_obj.apply_rules()
    output_success(f"Applied firewall rules to network '{net_obj.name}'", quiet=vctx.quiet)


@app.command("apply-dns")
@handle_errors()
def network_apply_dns(
    ctx: typer.Context,
    network: Annotated[str, typer.Argument(help="Network name or key")],
) -> None:
    """Apply pending DNS configuration to a network."""
    vctx = get_context(ctx)

    key = resolve_resource_id(vctx.client.networks, network, "network")
    net_obj = vctx.client.networks.get(key)

    if not net_obj.get("running"):
        typer.echo(
            f"Network '{net_obj.name}' is not running. DNS can only be applied to running networks.",
            err=True,
        )
        raise typer.Exit(1)

    net_obj.apply_dns()
    output_success(f"Applied DNS configuration to network '{net_obj.name}'", quiet=vctx.quiet)


@app.command("status")
@handle_errors()
def network_status(
    ctx: typer.Context,
    network: Annotated[str, typer.Argument(help="Network name or key")],
) -> None:
    """Show detailed status of a network including pending changes."""
    vctx = get_context(ctx)

    key = resolve_resource_id(vctx.client.networks, network, "network")
    net_obj = vctx.client.networks.get(key)

    status_data = {
        "name": net_obj.name,
        "$key": net_obj.key,
        "running": net_obj.get("running", False),
        "status": net_obj.get("status", "unknown"),
        "needs_restart": net_obj.get("need_restart", False),
        "needs_rule_apply": net_obj.get("need_fw_apply", False),
        "needs_dns_apply": net_obj.get("need_dns_apply", False),
        "needs_proxy_apply": net_obj.get("need_proxy_apply", False),
    }

    output_result(
        status_data,
        output_format=vctx.output_format,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


def _network_to_dict(net: Any) -> dict[str, Any]:
    """Convert a Network object to a dictionary for output."""
    return {
        "$key": net.key,
        "name": net.name,
        "description": net.get("description", ""),
        "type": net.get("type"),
        "network": net.get("network"),
        "ipaddress": net.get("ipaddress"),
        "gateway": net.get("gateway"),
        "mtu": net.get("mtu"),
        "status": net.get("status"),
        "running": net.get("running"),
        "dhcp_enabled": net.get("dhcp_enabled"),
        "dhcp_start": net.get("dhcp_start"),
        "dhcp_stop": net.get("dhcp_stop"),
        "dns": net.get("dns"),
        "domain": net.get("domain"),
        # Status flags for pending changes
        "needs_restart": net.get("need_restart", False),
        "needs_rule_apply": net.get("need_fw_apply", False),
        "needs_dns_apply": net.get("need_dns_apply", False),
    }
