"""Network host override commands for Verge CLI."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any, cast

if TYPE_CHECKING:
    from pyvergeos.resources.hosts import HostType

import typer

from verge_cli.columns import HOST_COLUMNS
from verge_cli.context import get_context
from verge_cli.errors import ResourceNotFoundError, handle_errors
from verge_cli.output import output_result, output_success
from verge_cli.utils import confirm_action, resolve_resource_id

app = typer.Typer(
    name="host",
    help=(
        "Manage per-network static host entries (DHCP reservations + DNS A"
        " records).\n\n"
        "A host override binds a **hostname** to an **IP address** inside a"
        " vnet's dnsmasq instance. Each entry serves a dual purpose: it"
        " installs a **DHCP static reservation** (`dhcp-host` in dnsmasq, so"
        " a client presenting the reserved hostname always gets the same IP)"
        " and, when the vnet has DNS enabled (`dns=simple` or `dns=bind`),"
        " auto-registers an **A record** for that hostname.\n\n"
        "Two entry types:\n\n"
        "- `host` (default) — single hostname → single IP.\n"
        "- `domain` — domain-wide override that applies to any host in the"
        " named domain.\n\n"
        "Hosts live inside a network and are identified by **hostname**,"
        " **IP address**, or **numeric key**. Use `-o json` for"
        " machine-readable output; `--query` against the `host`, `ip`, and"
        " `type` fields.\n\n"
        "---\n\n"
        "**Examples:**\n\n"
        "    # List static host entries on a network (JSON for agents)\n"
        "    vrg -o json network host list internal-prod\n\n"
        "    # Get a specific entry by hostname or IP\n"
        "    vrg network host get internal-prod database-01\n"
        "    vrg network host get internal-prod 10.0.1.50\n\n"
        "    # Reserve an IP for a VM (creates DHCP reservation + DNS A record)\n"
        "    vrg network host create internal-prod --hostname database-01"
        " --ip 10.0.1.50\n\n"
        "    # Domain-wide override\n"
        "    vrg network host create internal-prod --hostname example.com"
        " --ip 10.0.1.10 --type domain\n\n"
        "    # Update an entry's IP\n"
        "    vrg network host update internal-prod database-01 --ip 10.0.1.51\n\n"
        "    # Remove an entry (skip prompt with -y)\n"
        "    vrg network host delete internal-prod database-01 -y\n\n"
        "---\n\n"
        "**Notes:**\n\n"
        "Host changes are **staged**, not live. Creating, updating, or"
        " deleting entries sets a `need_dns_apply` flag on the network —"
        " dnsmasq keeps serving the previous configuration until you run"
        " `vrg network apply-dns <network>`, which regenerates the dnsmasq"
        " config and signals the daemon to reload **without restarting the"
        " container**. If the network is stopped, changes apply on next"
        " start.\n\n"
        "Use `vrg network status <network>` to see whether a network has"
        " pending DNS/DHCP changes waiting to be applied.\n\n"
        "Static host entries are keyed by **hostname**, not MAC address —"
        " dnsmasq matches incoming DHCP requests by the client-provided"
        " hostname and hands out the reserved IP. For broader network-level"
        " DHCP settings (pool range, dynamic assignment, gateway, domain),"
        " use `vrg network update`.\n\n"
        "Networks, and hosts within them, are identified by name or numeric"
        " key. Ambiguous network names return **exit code 7** (multiple"
        " matches); missing networks or hosts return **exit code 6** (not"
        " found)."
    ),
    no_args_is_help=True,
    rich_markup_mode="markdown",
)


def _resolve_host_id(network: Any, identifier: str) -> int:
    """Resolve a host hostname, IP, or ID to a key.

    Args:
        network: Network object with hosts collection.
        identifier: Host hostname, IP address, or numeric key.

    Returns:
        The host key.

    Raises:
        ResourceNotFoundError: If host not found.
    """
    hosts = network.hosts.list()
    for host in hosts:
        hostname = host.get("host") or getattr(host, "host", "")
        ip = host.get("ip") or getattr(host, "ip", "")
        key = host.get("$key") or getattr(host, "key", None)
        if (hostname == identifier or ip == identifier) and key is not None:
            return int(key)

    # If numeric, treat as key
    if identifier.isdigit():
        return int(identifier)

    raise ResourceNotFoundError(f"Host override '{identifier}' not found")


def _host_to_dict(host: Any) -> dict[str, Any]:
    """Convert a NetworkHost object to a dictionary for output.

    Args:
        host: Host object from SDK.

    Returns:
        Dictionary representation of the host.
    """
    return {
        "$key": host.get("$key") or getattr(host, "key", None),
        "host": host.get("host", ""),
        "ip": host.get("ip", ""),
        "type": host.get("type", "host"),
    }


@app.command("list")
@handle_errors()
def host_list(
    ctx: typer.Context,
    network: Annotated[str, typer.Argument(help="Network name or key")],
) -> None:
    """List DNS/DHCP host overrides for a network."""
    vctx = get_context(ctx)

    net_key = resolve_resource_id(vctx.client.networks, network, "network")
    net_obj = vctx.client.networks.get(net_key)

    hosts = net_obj.hosts.list()
    data = [_host_to_dict(host) for host in hosts]

    output_result(
        data,
        output_format=vctx.output_format,
        query=vctx.query,
        columns=HOST_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("get")
@handle_errors()
def host_get(
    ctx: typer.Context,
    network: Annotated[str, typer.Argument(help="Network name or key")],
    host: Annotated[str, typer.Argument(help="Host hostname, IP, or key")],
) -> None:
    """Get details of a DNS/DHCP host override."""
    vctx = get_context(ctx)

    net_key = resolve_resource_id(vctx.client.networks, network, "network")
    net_obj = vctx.client.networks.get(net_key)

    host_key = _resolve_host_id(net_obj, host)
    host_obj = net_obj.hosts.get(host_key)

    output_result(
        _host_to_dict(host_obj),
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("create")
@handle_errors()
def host_create(
    ctx: typer.Context,
    network: Annotated[str, typer.Argument(help="Network name or key")],
    hostname: Annotated[str, typer.Option("--hostname", "-n", help="Hostname for the mapping")],
    ip: Annotated[str, typer.Option("--ip", "-i", help="IP address to map to")],
    host_type: Annotated[
        str, typer.Option("--type", "-t", help="Type: 'host' (default) or 'domain'")
    ] = "host",
) -> None:
    """Create a new DNS/DHCP host override.

    Host overrides map hostnames to IP addresses for DNS resolution
    and DHCP static assignments. Changes require apply-dns to take effect.
    """
    vctx = get_context(ctx)

    net_key = resolve_resource_id(vctx.client.networks, network, "network")
    net_obj = vctx.client.networks.get(net_key)

    host_obj = net_obj.hosts.create(hostname=hostname, ip=ip, host_type=cast("HostType", host_type))

    output_success(
        f"Created host override '{host_obj.get('host', hostname)}' -> {host_obj.get('ip', ip)}",
        quiet=vctx.quiet,
    )

    output_result(
        _host_to_dict(host_obj),
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("update")
@handle_errors()
def host_update(
    ctx: typer.Context,
    network: Annotated[str, typer.Argument(help="Network name or key")],
    host: Annotated[str, typer.Argument(help="Host hostname, IP, or key")],
    hostname: Annotated[str | None, typer.Option("--hostname", "-n", help="New hostname")] = None,
    ip: Annotated[str | None, typer.Option("--ip", "-i", help="New IP address")] = None,
    host_type: Annotated[
        str | None, typer.Option("--type", "-t", help="New type: 'host' or 'domain'")
    ] = None,
) -> None:
    """Update a DNS/DHCP host override.

    Changes require apply-dns to take effect.
    """
    vctx = get_context(ctx)

    net_key = resolve_resource_id(vctx.client.networks, network, "network")
    net_obj = vctx.client.networks.get(net_key)

    host_key = _resolve_host_id(net_obj, host)
    existing = net_obj.hosts.get(host_key)

    # Check if any updates were specified
    if hostname is None and ip is None and host_type is None:
        typer.echo("No updates specified.", err=True)
        raise typer.Exit(2)

    # Merge updates with existing values
    new_hostname = hostname if hostname is not None else existing.get("host", "")
    new_ip = ip if ip is not None else existing.get("ip", "")
    new_type = host_type if host_type is not None else existing.get("type", "host")

    # SDK has hosts.update() so we can update directly
    host_obj = net_obj.hosts.update(
        host_key, hostname=new_hostname, ip=new_ip, host_type=cast("HostType", new_type)
    )

    output_success(f"Updated host override '{new_hostname}'", quiet=vctx.quiet)

    output_result(
        _host_to_dict(host_obj),
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("delete")
@handle_errors()
def host_delete(
    ctx: typer.Context,
    network: Annotated[str, typer.Argument(help="Network name or key")],
    host: Annotated[str, typer.Argument(help="Host hostname, IP, or key")],
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation")] = False,
) -> None:
    """Delete a DNS/DHCP host override.

    Changes require apply-dns to take effect.
    """
    vctx = get_context(ctx)

    net_key = resolve_resource_id(vctx.client.networks, network, "network")
    net_obj = vctx.client.networks.get(net_key)

    host_key = _resolve_host_id(net_obj, host)
    host_obj = net_obj.hosts.get(host_key)

    host_name = host_obj.get("host") or host_obj.get("ip", str(host_key))

    if not confirm_action(f"Delete host override '{host_name}'?", yes=yes):
        typer.echo("Cancelled.")
        raise typer.Exit(0)

    net_obj.hosts.delete(host_key)
    output_success(f"Deleted host override '{host_name}'", quiet=vctx.quiet)
