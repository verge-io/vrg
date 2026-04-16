"""Network firewall rule commands for Verge CLI."""

from __future__ import annotations

from typing import Annotated, Any

import click
import typer

from verge_cli.columns import RULE_COLUMNS
from verge_cli.context import get_context
from verge_cli.errors import ResourceNotFoundError, handle_errors
from verge_cli.output import output_result, output_success
from verge_cli.utils import confirm_action, resolve_resource_id

app = typer.Typer(
    name="rule",
    help="Manage network firewall rules.",
    no_args_is_help=True,
)


def _resolve_rule_id(network: Any, identifier: str) -> int:
    """Resolve a rule name or ID to a key.

    Args:
        network: Network object with rules collection.
        identifier: Rule name or numeric key.

    Returns:
        The rule key.

    Raises:
        ResourceNotFoundError: If rule not found.
    """
    # Try by name first
    rules = network.rules.list()
    for rule in rules:
        name = rule.get("name") or getattr(rule, "name", "")
        key = rule.get("$key") or getattr(rule, "key", None)
        if name == identifier and key is not None:
            return int(key)

    # If numeric, treat as key
    if identifier.isdigit():
        return int(identifier)

    raise ResourceNotFoundError(f"Rule '{identifier}' not found")


def _rule_to_dict(rule: Any) -> dict[str, Any]:
    """Convert a NetworkRule object to a dictionary for output.

    Args:
        rule: Rule object from SDK.

    Returns:
        Dictionary representation of the rule.
    """
    return {
        "$key": rule.key,
        "name": rule.get("name", ""),
        "description": rule.get("description", ""),
        "direction": rule.get("direction", "incoming"),
        "action": rule.get("action", "accept"),
        "protocol": rule.get("protocol", "any"),
        "interface": rule.get("interface", "auto"),
        "source_ip": rule.get("source_ip", ""),
        "source_ports": rule.get("source_ports", ""),
        "dest_ip": rule.get("destination_ip", ""),
        "dest_ports": rule.get("destination_ports", ""),
        "target_ip": rule.get("target_ip", ""),
        "target_ports": rule.get("target_ports", ""),
        "enabled": rule.get("enabled", True),
        "log": rule.get("log", False),
        "statistics": rule.get("statistics", False),
        "trace": rule.get("trace", False),
        "order": rule.get("orderid", 0),
        "system_rule": rule.get("system_rule", False),
        "packets": rule.get("packets", 0),
        "bytes": rule.get("bytes", 0),
    }


@app.command("list")
@handle_errors()
def rule_list(
    ctx: typer.Context,
    network: Annotated[str, typer.Argument(help="Network name or key")],
    direction: Annotated[
        str | None, typer.Option("--direction", "-d", help="Filter by direction")
    ] = None,
    action: Annotated[str | None, typer.Option("--action", "-a", help="Filter by action")] = None,
    enabled: Annotated[
        bool | None, typer.Option("--enabled/--disabled", help="Filter by enabled state")
    ] = None,
) -> None:
    """List firewall rules for a network."""
    vctx = get_context(ctx)

    net_key = resolve_resource_id(vctx.client.networks, network, "network")
    net_obj = vctx.client.networks.get(net_key)

    # Build filter kwargs
    filter_kwargs: dict[str, Any] = {}
    if direction:
        filter_kwargs["direction"] = direction
    if action:
        filter_kwargs["action"] = action
    if enabled is not None:
        filter_kwargs["enabled"] = enabled

    rules = net_obj.rules.list(**filter_kwargs)
    data = [_rule_to_dict(rule) for rule in rules]

    output_result(
        data,
        output_format=vctx.output_format,
        query=vctx.query,
        columns=RULE_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("get")
@handle_errors()
def rule_get(
    ctx: typer.Context,
    network: Annotated[str, typer.Argument(help="Network name or key")],
    rule: Annotated[str, typer.Argument(help="Rule name or key")],
) -> None:
    """Get details of a firewall rule."""
    vctx = get_context(ctx)

    net_key = resolve_resource_id(vctx.client.networks, network, "network")
    net_obj = vctx.client.networks.get(net_key)

    rule_key = _resolve_rule_id(net_obj, rule)
    rule_obj = net_obj.rules.get(rule_key)

    output_result(
        _rule_to_dict(rule_obj),
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("create")
@handle_errors()
def rule_create(
    ctx: typer.Context,
    network: Annotated[str, typer.Argument(help="Network name or key")],
    name: Annotated[str, typer.Option("--name", "-n", help="Rule name")],
    direction: Annotated[
        str, typer.Option("--direction", "-d", help="Direction (incoming/outgoing)")
    ] = "incoming",
    action: Annotated[
        str,
        typer.Option(
            "--action",
            "-a",
            help="Action",
            click_type=click.Choice(["accept", "drop", "reject", "translate", "route"]),
        ),
    ] = "accept",
    protocol: Annotated[
        str, typer.Option("--protocol", "-p", help="Protocol (tcp/udp/tcpudp/icmp/any)")
    ] = "any",
    interface: Annotated[
        str, typer.Option("--interface", help="Interface (auto/router/dmz/wireguard/any)")
    ] = "auto",
    source_ip: Annotated[
        str | None, typer.Option("--source-ip", help="Source IP/CIDR or alias:name")
    ] = None,
    source_ports: Annotated[str | None, typer.Option("--source-ports", help="Source ports")] = None,
    dest_ip: Annotated[
        str | None, typer.Option("--dest-ip", help="Destination IP/CIDR or alias:name")
    ] = None,
    dest_ports: Annotated[
        str | None, typer.Option("--dest-ports", help="Destination ports")
    ] = None,
    target_ip: Annotated[str | None, typer.Option("--target-ip", help="NAT target IP")] = None,
    target_ports: Annotated[
        str | None, typer.Option("--target-ports", help="NAT target ports")
    ] = None,
    enabled: Annotated[bool, typer.Option("--enabled/--disabled", help="Enable rule")] = True,
    log: Annotated[bool, typer.Option("--log/--no-log", help="Enable logging")] = False,
    stats: Annotated[bool, typer.Option("--stats/--no-stats", help="Enable statistics")] = False,
    order: Annotated[int | None, typer.Option("--order", help="Rule order position")] = None,
    description: Annotated[str, typer.Option("--description", help="Rule description")] = "",
) -> None:
    """Create a new firewall rule."""
    vctx = get_context(ctx)

    net_key = resolve_resource_id(vctx.client.networks, network, "network")
    net_obj = vctx.client.networks.get(net_key)

    create_kwargs: dict[str, Any] = {
        "name": name,
        "direction": direction,
        "action": action,
        "protocol": protocol,
        "interface": interface,
        "enabled": enabled,
        "log": log,
        "statistics": stats,
    }

    if source_ip:
        create_kwargs["source_ip"] = source_ip
    if source_ports:
        create_kwargs["source_ports"] = source_ports
    if dest_ip:
        create_kwargs["destination_ip"] = dest_ip
    if dest_ports:
        create_kwargs["destination_ports"] = dest_ports
    if target_ip:
        create_kwargs["target_ip"] = target_ip
    if target_ports:
        create_kwargs["target_ports"] = target_ports
    if order is not None:
        create_kwargs["order"] = order
    if description:
        create_kwargs["description"] = description

    rule_obj = net_obj.rules.create(**create_kwargs)

    output_success(f"Created rule '{rule_obj.name}' (key: {rule_obj.key})", quiet=vctx.quiet)

    output_result(
        _rule_to_dict(rule_obj),
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("update")
@handle_errors()
def rule_update(
    ctx: typer.Context,
    network: Annotated[str, typer.Argument(help="Network name or key")],
    rule: Annotated[str, typer.Argument(help="Rule name or key")],
    name: Annotated[str | None, typer.Option("--name", "-n", help="New rule name")] = None,
    direction: Annotated[str | None, typer.Option("--direction", "-d", help="Direction")] = None,
    action: Annotated[
        str | None,
        typer.Option(
            "--action",
            "-a",
            help="Action",
            click_type=click.Choice(["accept", "drop", "reject", "translate", "route"]),
        ),
    ] = None,
    protocol: Annotated[str | None, typer.Option("--protocol", "-p", help="Protocol")] = None,
    interface: Annotated[str | None, typer.Option("--interface", help="Interface")] = None,
    source_ip: Annotated[str | None, typer.Option("--source-ip", help="Source IP")] = None,
    source_ports: Annotated[str | None, typer.Option("--source-ports", help="Source ports")] = None,
    dest_ip: Annotated[str | None, typer.Option("--dest-ip", help="Destination IP")] = None,
    dest_ports: Annotated[
        str | None, typer.Option("--dest-ports", help="Destination ports")
    ] = None,
    target_ip: Annotated[str | None, typer.Option("--target-ip", help="NAT target IP")] = None,
    target_ports: Annotated[
        str | None, typer.Option("--target-ports", help="NAT target ports")
    ] = None,
    enabled: Annotated[
        bool | None, typer.Option("--enabled/--disabled", help="Enable/disable rule")
    ] = None,
    log: Annotated[
        bool | None, typer.Option("--log/--no-log", help="Enable/disable logging")
    ] = None,
    stats: Annotated[
        bool | None, typer.Option("--stats/--no-stats", help="Enable/disable statistics")
    ] = None,
    description: Annotated[
        str | None, typer.Option("--description", help="Rule description")
    ] = None,
) -> None:
    """Update a firewall rule."""
    vctx = get_context(ctx)

    net_key = resolve_resource_id(vctx.client.networks, network, "network")
    net_obj = vctx.client.networks.get(net_key)

    rule_key = _resolve_rule_id(net_obj, rule)

    # Build update kwargs (only non-None values)
    updates: dict[str, Any] = {}
    if name is not None:
        updates["name"] = name
    if direction is not None:
        updates["direction"] = direction
    if action is not None:
        updates["action"] = action
    if protocol is not None:
        updates["protocol"] = protocol
    if interface is not None:
        updates["interface"] = interface
    if source_ip is not None:
        updates["source_ip"] = source_ip
    if source_ports is not None:
        updates["source_ports"] = source_ports
    if dest_ip is not None:
        updates["destination_ip"] = dest_ip
    if dest_ports is not None:
        updates["destination_ports"] = dest_ports
    if target_ip is not None:
        updates["target_ip"] = target_ip
    if target_ports is not None:
        updates["target_ports"] = target_ports
    if enabled is not None:
        updates["enabled"] = enabled
    if log is not None:
        updates["log"] = log
    if stats is not None:
        updates["statistics"] = stats
    if description is not None:
        updates["description"] = description

    if not updates:
        typer.echo("No updates specified.", err=True)
        raise typer.Exit(2)

    rule_obj = net_obj.rules.update(rule_key, **updates)

    output_success(f"Updated rule '{rule_obj.name}'", quiet=vctx.quiet)

    output_result(
        _rule_to_dict(rule_obj),
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("delete")
@handle_errors()
def rule_delete(
    ctx: typer.Context,
    network: Annotated[str, typer.Argument(help="Network name or key")],
    rule: Annotated[str, typer.Argument(help="Rule name or key")],
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation")] = False,
) -> None:
    """Delete a firewall rule."""
    vctx = get_context(ctx)

    net_key = resolve_resource_id(vctx.client.networks, network, "network")
    net_obj = vctx.client.networks.get(net_key)

    rule_key = _resolve_rule_id(net_obj, rule)
    rule_obj = net_obj.rules.get(rule_key)

    rule_name = rule_obj.get("name", rule_key)

    if not confirm_action(f"Delete rule '{rule_name}'?", yes=yes):
        typer.echo("Cancelled.")
        raise typer.Exit(0)

    net_obj.rules.delete(rule_key)
    output_success(f"Deleted rule '{rule_name}'", quiet=vctx.quiet)


@app.command("enable")
@handle_errors()
def rule_enable(
    ctx: typer.Context,
    network: Annotated[str, typer.Argument(help="Network name or key")],
    rule: Annotated[str, typer.Argument(help="Rule name or key")],
) -> None:
    """Enable a firewall rule."""
    vctx = get_context(ctx)

    net_key = resolve_resource_id(vctx.client.networks, network, "network")
    net_obj = vctx.client.networks.get(net_key)

    rule_key = _resolve_rule_id(net_obj, rule)
    rule_obj = net_obj.rules.get(rule_key)

    rule_obj.enable()
    output_success(f"Enabled rule '{rule_obj.name}'", quiet=vctx.quiet)


@app.command("disable")
@handle_errors()
def rule_disable(
    ctx: typer.Context,
    network: Annotated[str, typer.Argument(help="Network name or key")],
    rule: Annotated[str, typer.Argument(help="Rule name or key")],
) -> None:
    """Disable a firewall rule."""
    vctx = get_context(ctx)

    net_key = resolve_resource_id(vctx.client.networks, network, "network")
    net_obj = vctx.client.networks.get(net_key)

    rule_key = _resolve_rule_id(net_obj, rule)
    rule_obj = net_obj.rules.get(rule_key)

    rule_obj.disable()
    output_success(f"Disabled rule '{rule_obj.name}'", quiet=vctx.quiet)
