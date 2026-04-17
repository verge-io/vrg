"""Network DNS zone and record commands for Verge CLI."""

from __future__ import annotations

from typing import Annotated, Any

import typer

from verge_cli.columns import RECORD_COLUMNS, VIEW_COLUMNS, ZONE_COLUMNS
from verge_cli.context import get_context
from verge_cli.errors import ResourceNotFoundError, handle_errors
from verge_cli.output import output_result, output_success
from verge_cli.utils import confirm_action, resolve_resource_id

# Main DNS app
app = typer.Typer(
    name="dns",
    help=(
        "Manage per-network DNS: views, zones, and records.\n\n"
        "Every VergeOS virtual network runs its own DNS service inside the"
        " vnet container. The network's `dns` field selects the engine:"
        " `disabled`, `simple` (dnsmasq forwarder with auto A records for"
        " DHCP clients), `network` (forward to another vnet), or `bind`"
        " (full BIND9 authoritative server). **Views, zones, and records"
        " are only meaningful in `bind` mode** — in `simple` mode, DNS is"
        " managed purely through the network's upstream `dnslist` and"
        " DHCP-driven auto-registration.\n\n"
        "**Resource hierarchy (BIND mode):**\n\n"
        "- **View** — client-matching policy (split-horizon). Contains"
        " `match_clients` ACLs, `recursion` toggle, cache size.\n"
        "- **Zone** — a domain served by a view. `master`, `slave`,"
        " `forward`, `redirect`, `stub`, or `static-stub`.\n"
        "- **Record** — A, AAAA, CNAME, MX, TXT, NS, PTR, SRV, or CAA"
        " entries within a zone.\n\n"
        "Views are processed in order — the first view whose"
        " `match_clients` ACL matches the querying client handles the"
        " request. Use this to serve internal IPs to LAN clients and"
        " public IPs to the internet for the same domain.\n\n"
        "Networks, views, zones, and records are all identified by name"
        " or numeric key. Use `-o json` for machine-readable output.\n\n"
        "---\n\n"
        "**Examples:**\n\n"
        "    # List DNS views on a network (JSON for agents)\n"
        "    vrg -o json network dns view list internal-prod\n\n"
        "    # Create an internal split-horizon view with recursion\n"
        "    vrg network dns view create internal-prod --name internal"
        " --recursion --match-clients '10.0.0.0/8,192.168.0.0/16'\n\n"
        "    # Create an external (authoritative-only) view\n"
        "    vrg network dns view create internal-prod --name external"
        " --no-recursion --match-clients '0.0.0.0/0'\n\n"
        "    # List zones in a view\n"
        "    vrg network dns zone list internal-prod internal\n\n"
        "    # Create a master zone\n"
        "    vrg network dns zone create internal-prod internal"
        " --domain example.com --type master\n\n"
        "    # Add records to the zone\n"
        "    vrg network dns record create internal-prod internal"
        " example.com --name www --type A --value 10.0.1.50\n"
        "    vrg network dns record create internal-prod internal"
        " example.com --name @ --type MX --value mail.example.com"
        " --priority 10\n\n"
        "    # List/filter records by type\n"
        "    vrg network dns record list internal-prod internal"
        " example.com --type A\n\n"
        "    # Apply staged DNS changes (regenerate zone files and reload)\n"
        "    vrg network apply-dns internal-prod\n\n"
        "---\n\n"
        "**Notes:**\n\n"
        "DNS changes are **staged**, not live. `view`, `zone`, and"
        " `record` create/update/delete operations set a `need_dns_apply`"
        " flag on the network — existing resolvers keep answering under"
        " the previous configuration until you run"
        " `vrg network apply-dns <network>`, which regenerates zone files"
        " and reloads BIND (or dnsmasq) **without restarting the"
        " container**. If the network is stopped, changes apply on next"
        " start.\n\n"
        "Use `vrg network status <network>` to check whether a network"
        " has pending DNS changes waiting to be applied. SOA"
        " `serial_number` is auto-incremented on record changes.\n\n"
        "View `match_clients` accepts comma-separated CIDRs (e.g."
        " `10.0.0.0/8,192.168.0.0/16`) which vrg converts to the"
        " semicolon-delimited ACL format BIND expects. Prefix with `!`"
        " to negate (e.g. `!192.168.1.0/24;any;`)."
    ),
    no_args_is_help=True,
    rich_markup_mode="markdown",
)

# Zone subapp
zone_app = typer.Typer(
    name="zone",
    help=(
        "Manage BIND DNS zones within a view.\n\n"
        "A zone is a domain (or subdomain) served by a view. Zone"
        " operations take the network, view, and zone as positional"
        " arguments. Changes are staged — run `vrg network apply-dns"
        " <network>` to activate."
    ),
    no_args_is_help=True,
    rich_markup_mode="markdown",
)

# Record subapp
record_app = typer.Typer(
    name="record",
    help=(
        "Manage DNS records within a zone.\n\n"
        "Supported types: A, AAAA, CNAME, MX, TXT, NS, PTR, SRV, CAA."
        " Record operations take network, view, and zone as positional"
        " arguments. Use `--priority` for MX/SRV records. Changes are"
        " staged — run `vrg network apply-dns <network>` to activate."
    ),
    no_args_is_help=True,
    rich_markup_mode="markdown",
)

# View subapp
view_app = typer.Typer(
    name="view",
    help=(
        "Manage BIND DNS views on a network.\n\n"
        "Views implement split-horizon DNS by matching queries against"
        " client IP ACLs. Views are evaluated in order; the first"
        " matching view handles the query. `match_clients` accepts"
        " comma-separated CIDRs (vrg converts to BIND's semicolon"
        " format). Changes are staged — run `vrg network apply-dns"
        " <network>` to activate."
    ),
    no_args_is_help=True,
    rich_markup_mode="markdown",
)

# Register subapps
app.add_typer(zone_app, name="zone")
app.add_typer(record_app, name="record")
app.add_typer(view_app, name="view")


# =============================================================================
# Zone Helper Functions
# =============================================================================


def _resolve_zone_id(view: Any, identifier: str) -> int:
    """Resolve a zone domain or ID to a key.

    Args:
        view: View object with zones collection.
        identifier: Zone domain or numeric key.

    Returns:
        The zone key.

    Raises:
        ResourceNotFoundError: If zone not found.
    """
    # If numeric, treat as key directly
    if identifier.isdigit():
        return int(identifier)

    # Try to find by domain name
    zones = view.zones.list()
    for zone in zones:
        domain = zone.get("domain") or getattr(zone, "domain", "")
        key = zone.get("$key") or getattr(zone, "key", None)
        if domain == identifier and key is not None:
            return int(key)

    raise ResourceNotFoundError(f"DNS zone '{identifier}' not found")


def _zone_to_dict(zone: Any) -> dict[str, Any]:
    """Convert a DNS Zone object to a dictionary for output.

    Args:
        zone: Zone object from SDK.

    Returns:
        Dictionary representation of the zone.
    """
    return {
        "id": zone.get("$key") or getattr(zone, "key", None),
        "domain": zone.get("domain", ""),
        "type": zone.get("type", "master"),
        "view_name": zone.get("view_name") or getattr(zone, "view_name", None),
        "serial": zone.get("serial_number", 0),
        "nameserver": zone.get("nameserver", ""),
        "email": zone.get("email", ""),
        "default_ttl": zone.get("default_ttl", ""),
    }


# =============================================================================
# Record Helper Functions
# =============================================================================


def _resolve_record_id(zone: Any, identifier: str) -> int:
    """Resolve a record name or ID to a key.

    Args:
        zone: Zone object with records collection.
        identifier: Record name or numeric key.

    Returns:
        The record key.

    Raises:
        ResourceNotFoundError: If record not found.
    """
    # If numeric, treat as key directly
    if identifier.isdigit():
        return int(identifier)

    # Try to find by name
    records = zone.records.list()
    for record in records:
        host = record.get("host") or getattr(record, "host", "")
        key = record.get("$key") or getattr(record, "key", None)
        if host == identifier and key is not None:
            return int(key)

    raise ResourceNotFoundError(f"DNS record '{identifier}' not found")


def _record_to_dict(record: Any) -> dict[str, Any]:
    """Convert a DNS Record object to a dictionary for output.

    Args:
        record: Record object from SDK.

    Returns:
        Dictionary representation of the record.
    """
    return {
        "id": record.get("$key") or getattr(record, "key", None),
        "host": record.get("host", ""),
        "type": record.get("type", "A"),
        "value": record.get("value", ""),
        "ttl": record.get("ttl", ""),
        "priority": record.get("mx_preference", 0),
        "weight": record.get("weight", 0),
        "port": record.get("port", 0),
        "description": record.get("description", ""),
    }


# =============================================================================
# View Helper Functions
# =============================================================================


def _transform_comma_to_semicolon(value: str | None) -> str | None:
    """Transform comma-separated values to semicolon-delimited format for SDK.

    Args:
        value: Comma-separated string (e.g., "10.0.0.0/8,192.168.0.0/16")

    Returns:
        Semicolon-delimited string with trailing semicolon (e.g., "10.0.0.0/8;192.168.0.0/16;")
        or None if input is None.
    """
    if value is None:
        return None
    # Split by comma, strip whitespace, rejoin with semicolons
    parts = [p.strip() for p in value.split(",") if p.strip()]
    if not parts:
        return None
    return ";".join(parts) + ";"


def _resolve_view_id(network: Any, identifier: str) -> int:
    """Resolve a view name or ID to a key.

    Args:
        network: Network object with dns_views collection.
        identifier: View name or numeric key.

    Returns:
        The view key.

    Raises:
        ResourceNotFoundError: If view not found.
    """
    # If numeric, treat as key directly
    if identifier.isdigit():
        return int(identifier)

    # Try to find by name
    views = network.dns_views.list()
    for view in views:
        name = view.get("name") or getattr(view, "name", "")
        key = view.get("$key") or getattr(view, "key", None)
        if name == identifier and key is not None:
            return int(key)

    raise ResourceNotFoundError(f"DNS view '{identifier}' not found")


def _view_to_dict(view: Any) -> dict[str, Any]:
    """Convert a DNS View object to a dictionary for output.

    Args:
        view: View object from SDK.

    Returns:
        Dictionary representation of the view.
    """
    match_clients = view.get("match_clients", "")
    # Transform semicolon-delimited back to comma-separated for display
    if match_clients:
        match_clients = match_clients.replace(";", ", ").rstrip(", ")

    return {
        "id": view.get("$key") or getattr(view, "key", None),
        "name": view.get("name", ""),
        "recursion": view.get("recursion", False),
        "match_clients": match_clients,
        "max_cache_size": view.get("max_cache_size", 0),
    }


# =============================================================================
# Zone Commands
# =============================================================================


@zone_app.command("list")
@handle_errors()
def zone_list(
    ctx: typer.Context,
    network: Annotated[str, typer.Argument(help="Network name or key")],
    view: Annotated[str, typer.Argument(help="View name or key")],
) -> None:
    """List DNS zones for a view.

    Shows all BIND DNS zones configured in the view.
    Changes require apply-dns to take effect.
    """
    vctx = get_context(ctx)

    net_key = resolve_resource_id(vctx.client.networks, network, "network")
    net_obj = vctx.client.networks.get(net_key)

    view_key = _resolve_view_id(net_obj, view)
    view_obj = net_obj.dns_views.get(view_key)

    zones = view_obj.zones.list()
    data = [_zone_to_dict(zone) for zone in zones]

    output_result(
        data,
        output_format=vctx.output_format,
        query=vctx.query,
        columns=ZONE_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@zone_app.command("get")
@handle_errors()
def zone_get(
    ctx: typer.Context,
    network: Annotated[str, typer.Argument(help="Network name or key")],
    view: Annotated[str, typer.Argument(help="View name or key")],
    zone: Annotated[str, typer.Argument(help="Zone domain or key")],
) -> None:
    """Get details of a DNS zone."""
    vctx = get_context(ctx)

    net_key = resolve_resource_id(vctx.client.networks, network, "network")
    net_obj = vctx.client.networks.get(net_key)

    view_key = _resolve_view_id(net_obj, view)
    view_obj = net_obj.dns_views.get(view_key)

    zone_key = _resolve_zone_id(view_obj, zone)
    zone_obj = view_obj.zones.get(zone_key)

    output_result(
        _zone_to_dict(zone_obj),
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@zone_app.command("create")
@handle_errors()
def zone_create(
    ctx: typer.Context,
    network: Annotated[str, typer.Argument(help="Network name or key")],
    view: Annotated[str, typer.Argument(help="View name or key")],
    domain: Annotated[str, typer.Option("--domain", "-d", help="Zone domain name")],
    zone_type: Annotated[
        str, typer.Option("--type", "-t", help="Zone type (master/slave)")
    ] = "master",
) -> None:
    """Create a new DNS zone.

    Creates a BIND DNS zone in the view. Zone commands work on
    networks with BIND enabled. Changes require apply-dns to take effect.
    """
    vctx = get_context(ctx)

    net_key = resolve_resource_id(vctx.client.networks, network, "network")
    net_obj = vctx.client.networks.get(net_key)

    view_key = _resolve_view_id(net_obj, view)
    view_obj = net_obj.dns_views.get(view_key)

    create_kwargs: dict[str, Any] = {
        "domain": domain,
        "type": zone_type,
    }

    zone_obj = view_obj.zones.create(**create_kwargs)

    zone_domain = zone_obj.get("domain") or getattr(zone_obj, "domain", "")
    zone_key_val = zone_obj.get("$key") or zone_obj.key
    output_success(f"Created DNS zone '{zone_domain}' (key: {zone_key_val})", quiet=vctx.quiet)

    output_result(
        _zone_to_dict(zone_obj),
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@zone_app.command("update")
@handle_errors()
def zone_update(
    ctx: typer.Context,
    network: Annotated[str, typer.Argument(help="Network name or key")],
    view: Annotated[str, typer.Argument(help="View name or key")],
    zone: Annotated[str, typer.Argument(help="Zone domain or key")],
    domain: Annotated[str | None, typer.Option("--domain", "-d", help="New domain name")] = None,
    zone_type: Annotated[
        str | None, typer.Option("--type", "-t", help="Zone type (master/slave)")
    ] = None,
) -> None:
    """Update a DNS zone.

    Changes require apply-dns to take effect.
    """
    vctx = get_context(ctx)

    net_key = resolve_resource_id(vctx.client.networks, network, "network")
    net_obj = vctx.client.networks.get(net_key)

    view_key = _resolve_view_id(net_obj, view)
    view_obj = net_obj.dns_views.get(view_key)

    zone_key = _resolve_zone_id(view_obj, zone)

    # Build update kwargs (only non-None values)
    updates: dict[str, Any] = {}
    if domain is not None:
        updates["domain"] = domain
    if zone_type is not None:
        updates["type"] = zone_type

    if not updates:
        typer.echo("No updates specified.", err=True)
        raise typer.Exit(2)

    zone_obj = view_obj.zones.update(zone_key, **updates)

    zone_domain = zone_obj.get("domain") or getattr(zone_obj, "domain", "")
    output_success(f"Updated DNS zone '{zone_domain}'", quiet=vctx.quiet)

    output_result(
        _zone_to_dict(zone_obj),
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@zone_app.command("delete")
@handle_errors()
def zone_delete(
    ctx: typer.Context,
    network: Annotated[str, typer.Argument(help="Network name or key")],
    view: Annotated[str, typer.Argument(help="View name or key")],
    zone: Annotated[str, typer.Argument(help="Zone domain or key")],
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation")] = False,
) -> None:
    """Delete a DNS zone.

    This will delete the zone and all its records.
    Changes require apply-dns to take effect.
    """
    vctx = get_context(ctx)

    net_key = resolve_resource_id(vctx.client.networks, network, "network")
    net_obj = vctx.client.networks.get(net_key)

    view_key = _resolve_view_id(net_obj, view)
    view_obj = net_obj.dns_views.get(view_key)

    zone_key = _resolve_zone_id(view_obj, zone)
    zone_obj = view_obj.zones.get(zone_key)

    zone_domain = zone_obj.get("domain") or str(zone_key)

    if not confirm_action(f"Delete DNS zone '{zone_domain}' and all its records?", yes=yes):
        typer.echo("Cancelled.")
        raise typer.Exit(0)

    view_obj.zones.delete(zone_key)
    output_success(f"Deleted DNS zone '{zone_domain}'", quiet=vctx.quiet)


# =============================================================================
# Record Commands
# =============================================================================


@record_app.command("list")
@handle_errors()
def record_list(
    ctx: typer.Context,
    network: Annotated[str, typer.Argument(help="Network name or key")],
    view: Annotated[str, typer.Argument(help="View name or key")],
    zone: Annotated[str, typer.Argument(help="Zone domain or key")],
    record_type: Annotated[
        str | None, typer.Option("--type", "-t", help="Filter by record type (A/AAAA/CNAME/MX/TXT)")
    ] = None,
) -> None:
    """List DNS records for a zone.

    Shows all DNS records in the specified zone.
    Changes require apply-dns to take effect.
    """
    vctx = get_context(ctx)

    net_key = resolve_resource_id(vctx.client.networks, network, "network")
    net_obj = vctx.client.networks.get(net_key)

    view_key = _resolve_view_id(net_obj, view)
    view_obj = net_obj.dns_views.get(view_key)

    zone_key = _resolve_zone_id(view_obj, zone)
    zone_obj = view_obj.zones.get(zone_key)

    # Build filter kwargs
    filter_kwargs: dict[str, Any] = {}
    if record_type:
        filter_kwargs["type"] = record_type

    records = zone_obj.records.list(**filter_kwargs)
    data = [_record_to_dict(record) for record in records]

    output_result(
        data,
        output_format=vctx.output_format,
        query=vctx.query,
        columns=RECORD_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@record_app.command("get")
@handle_errors()
def record_get(
    ctx: typer.Context,
    network: Annotated[str, typer.Argument(help="Network name or key")],
    view: Annotated[str, typer.Argument(help="View name or key")],
    zone: Annotated[str, typer.Argument(help="Zone domain or key")],
    record: Annotated[str, typer.Argument(help="Record ID")],
) -> None:
    """Get details of a DNS record."""
    vctx = get_context(ctx)

    net_key = resolve_resource_id(vctx.client.networks, network, "network")
    net_obj = vctx.client.networks.get(net_key)

    view_key = _resolve_view_id(net_obj, view)
    view_obj = net_obj.dns_views.get(view_key)

    zone_key = _resolve_zone_id(view_obj, zone)
    zone_obj = view_obj.zones.get(zone_key)

    record_key = _resolve_record_id(zone_obj, record)
    record_obj = zone_obj.records.get(record_key)

    output_result(
        _record_to_dict(record_obj),
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@record_app.command("create")
@handle_errors()
def record_create(
    ctx: typer.Context,
    network: Annotated[str, typer.Argument(help="Network name or key")],
    view: Annotated[str, typer.Argument(help="View name or key")],
    zone: Annotated[str, typer.Argument(help="Zone domain or key")],
    name: Annotated[str, typer.Option("--name", "-n", help="Record name (e.g., www, @, mail)")],
    record_type: Annotated[
        str, typer.Option("--type", "-t", help="Record type (A/AAAA/CNAME/MX/TXT/NS/PTR/SRV)")
    ],
    value: Annotated[
        str, typer.Option("--value", "-v", help="Record value (IP, hostname, or text)")
    ],
    ttl: Annotated[int, typer.Option("--ttl", help="Time to live in seconds")] = 3600,
    priority: Annotated[
        int | None, typer.Option("--priority", "-p", help="Priority (for MX/SRV records)")
    ] = None,
) -> None:
    """Create a new DNS record.

    Creates a DNS record in the specified zone.
    Changes require apply-dns to take effect.

    Examples:
        vrg network dns record create mynet internal example.com --name www --type A --value 10.0.0.100
        vrg network dns record create mynet internal example.com --name @ --type MX --value mail.example.com --priority 10
    """
    vctx = get_context(ctx)

    net_key = resolve_resource_id(vctx.client.networks, network, "network")
    net_obj = vctx.client.networks.get(net_key)

    view_key = _resolve_view_id(net_obj, view)
    view_obj = net_obj.dns_views.get(view_key)

    zone_key = _resolve_zone_id(view_obj, zone)
    zone_obj = view_obj.zones.get(zone_key)

    create_kwargs: dict[str, Any] = {
        "host": name,
        "record_type": record_type,
        "value": value,
        "ttl": ttl,
    }

    if priority is not None:
        create_kwargs["mx_preference"] = priority

    record_obj = zone_obj.records.create(**create_kwargs)

    record_host = record_obj.get("host") or name
    record_value = record_obj.get("value") or value
    output_success(f"Created DNS record '{record_host}' -> {record_value}", quiet=vctx.quiet)

    output_result(
        _record_to_dict(record_obj),
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@record_app.command("update")
@handle_errors()
def record_update(
    ctx: typer.Context,
    network: Annotated[str, typer.Argument(help="Network name or key")],
    view: Annotated[str, typer.Argument(help="View name or key")],
    zone: Annotated[str, typer.Argument(help="Zone domain or key")],
    record: Annotated[str, typer.Argument(help="Record ID")],
    name: Annotated[str | None, typer.Option("--name", "-n", help="New record name")] = None,
    record_type: Annotated[str | None, typer.Option("--type", "-t", help="Record type")] = None,
    value: Annotated[
        str | None, typer.Option("--value", "-v", help="New record value (IP, hostname, or text)")
    ] = None,
    ttl: Annotated[int | None, typer.Option("--ttl", help="Time to live")] = None,
    priority: Annotated[int | None, typer.Option("--priority", "-p", help="Priority")] = None,
) -> None:
    """Update a DNS record.

    Changes require apply-dns to take effect.
    """
    vctx = get_context(ctx)

    net_key = resolve_resource_id(vctx.client.networks, network, "network")
    net_obj = vctx.client.networks.get(net_key)

    view_key = _resolve_view_id(net_obj, view)
    view_obj = net_obj.dns_views.get(view_key)

    zone_key = _resolve_zone_id(view_obj, zone)
    zone_obj = view_obj.zones.get(zone_key)

    record_key = _resolve_record_id(zone_obj, record)

    # Build update kwargs (only non-None values)
    updates: dict[str, Any] = {}
    if name is not None:
        updates["host"] = name
    if record_type is not None:
        updates["type"] = record_type
    if value is not None:
        updates["value"] = value
    if ttl is not None:
        updates["ttl"] = ttl
    if priority is not None:
        updates["mx_preference"] = priority

    if not updates:
        typer.echo("No updates specified.", err=True)
        raise typer.Exit(2)

    record_obj = zone_obj.records.update(record_key, **updates)

    record_host = record_obj.get("host") or record
    output_success(f"Updated DNS record '{record_host}'", quiet=vctx.quiet)

    output_result(
        _record_to_dict(record_obj),
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@record_app.command("delete")
@handle_errors()
def record_delete(
    ctx: typer.Context,
    network: Annotated[str, typer.Argument(help="Network name or key")],
    view: Annotated[str, typer.Argument(help="View name or key")],
    zone: Annotated[str, typer.Argument(help="Zone domain or key")],
    record: Annotated[str, typer.Argument(help="Record ID")],
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation")] = False,
) -> None:
    """Delete a DNS record.

    Changes require apply-dns to take effect.
    """
    vctx = get_context(ctx)

    net_key = resolve_resource_id(vctx.client.networks, network, "network")
    net_obj = vctx.client.networks.get(net_key)

    view_key = _resolve_view_id(net_obj, view)
    view_obj = net_obj.dns_views.get(view_key)

    zone_key = _resolve_zone_id(view_obj, zone)
    zone_obj = view_obj.zones.get(zone_key)

    record_key = _resolve_record_id(zone_obj, record)
    record_obj = zone_obj.records.get(record_key)

    record_host = record_obj.get("host") or str(record_key)

    if not confirm_action(f"Delete DNS record '{record_host}'?", yes=yes):
        typer.echo("Cancelled.")
        raise typer.Exit(0)

    zone_obj.records.delete(record_key)
    output_success(f"Deleted DNS record '{record_host}'", quiet=vctx.quiet)


# =============================================================================
# View Commands
# =============================================================================


@view_app.command("list")
@handle_errors()
def view_list(
    ctx: typer.Context,
    network: Annotated[str, typer.Argument(help="Network name or key")],
) -> None:
    """List DNS views for a network.

    DNS views enable split-horizon DNS where different clients see
    different responses for the same domain.
    """
    vctx = get_context(ctx)

    net_key = resolve_resource_id(vctx.client.networks, network, "network")
    net_obj = vctx.client.networks.get(net_key)

    views = net_obj.dns_views.list()
    data = [_view_to_dict(view) for view in views]

    output_result(
        data,
        output_format=vctx.output_format,
        query=vctx.query,
        columns=VIEW_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@view_app.command("get")
@handle_errors()
def view_get(
    ctx: typer.Context,
    network: Annotated[str, typer.Argument(help="Network name or key")],
    view: Annotated[str, typer.Argument(help="View name or key")],
) -> None:
    """Get details of a DNS view."""
    vctx = get_context(ctx)

    net_key = resolve_resource_id(vctx.client.networks, network, "network")
    net_obj = vctx.client.networks.get(net_key)

    view_key = _resolve_view_id(net_obj, view)
    view_obj = net_obj.dns_views.get(view_key)

    output_result(
        _view_to_dict(view_obj),
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@view_app.command("create")
@handle_errors()
def view_create(
    ctx: typer.Context,
    network: Annotated[str, typer.Argument(help="Network name or key")],
    name: Annotated[str, typer.Option("--name", "-n", help="View name")],
    recursion: Annotated[
        bool, typer.Option("--recursion/--no-recursion", help="Enable recursive DNS queries")
    ] = False,
    match_clients: Annotated[
        str | None,
        typer.Option("--match-clients", help="Client networks to match (comma-separated CIDRs)"),
    ] = None,
    match_destinations: Annotated[
        str | None,
        typer.Option(
            "--match-destinations", help="Destination networks to match (comma-separated CIDRs)"
        ),
    ] = None,
    max_cache_size: Annotated[
        int, typer.Option("--max-cache-size", help="Max RAM for DNS cache in bytes")
    ] = 33554432,
) -> None:
    """Create a new DNS view.

    DNS views enable split-horizon DNS where different clients see
    different responses for the same domain. Changes require apply-dns.

    Examples:
        vrg network dns view create mynet --name internal --recursion
        vrg network dns view create mynet --name external --match-clients "0.0.0.0/0"
    """
    vctx = get_context(ctx)

    net_key = resolve_resource_id(vctx.client.networks, network, "network")
    net_obj = vctx.client.networks.get(net_key)

    create_kwargs: dict[str, Any] = {
        "name": name,
        "recursion": recursion,
        "max_cache_size": max_cache_size,
    }

    # Transform comma-separated to semicolon-delimited
    if match_clients:
        create_kwargs["match_clients"] = _transform_comma_to_semicolon(match_clients)
    if match_destinations:
        create_kwargs["match_destinations"] = _transform_comma_to_semicolon(match_destinations)

    view_obj = net_obj.dns_views.create(**create_kwargs)

    view_name = view_obj.get("name") or name
    view_key = view_obj.get("$key") or getattr(view_obj, "key", None)
    output_success(f"Created DNS view '{view_name}' (id: {view_key})", quiet=vctx.quiet)

    output_result(
        _view_to_dict(view_obj),
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@view_app.command("update")
@handle_errors()
def view_update(
    ctx: typer.Context,
    network: Annotated[str, typer.Argument(help="Network name or key")],
    view: Annotated[str, typer.Argument(help="View name or key")],
    name: Annotated[str | None, typer.Option("--name", "-n", help="New view name")] = None,
    recursion: Annotated[
        bool | None, typer.Option("--recursion/--no-recursion", help="Enable recursive DNS")
    ] = None,
    match_clients: Annotated[
        str | None, typer.Option("--match-clients", help="Client networks (comma-separated)")
    ] = None,
    match_destinations: Annotated[
        str | None, typer.Option("--match-destinations", help="Destination networks")
    ] = None,
    max_cache_size: Annotated[
        int | None, typer.Option("--max-cache-size", help="Max cache size in bytes")
    ] = None,
) -> None:
    """Update a DNS view.

    Changes require apply-dns to take effect.
    """
    vctx = get_context(ctx)

    net_key = resolve_resource_id(vctx.client.networks, network, "network")
    net_obj = vctx.client.networks.get(net_key)

    view_key = _resolve_view_id(net_obj, view)

    # Build update kwargs (only non-None values)
    updates: dict[str, Any] = {}
    if name is not None:
        updates["name"] = name
    if recursion is not None:
        updates["recursion"] = recursion
    if match_clients is not None:
        updates["match_clients"] = _transform_comma_to_semicolon(match_clients)
    if match_destinations is not None:
        updates["match_destinations"] = _transform_comma_to_semicolon(match_destinations)
    if max_cache_size is not None:
        updates["max_cache_size"] = max_cache_size

    if not updates:
        typer.echo("No updates specified.", err=True)
        raise typer.Exit(2)

    view_obj = net_obj.dns_views.update(view_key, **updates)

    view_name = view_obj.get("name") or view
    output_success(f"Updated DNS view '{view_name}'", quiet=vctx.quiet)

    output_result(
        _view_to_dict(view_obj),
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@view_app.command("delete")
@handle_errors()
def view_delete(
    ctx: typer.Context,
    network: Annotated[str, typer.Argument(help="Network name or key")],
    view: Annotated[str, typer.Argument(help="View name or key")],
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation")] = False,
) -> None:
    """Delete a DNS view.

    This will delete the view and all its zones and records.
    Changes require apply-dns to take effect.
    """
    vctx = get_context(ctx)

    net_key = resolve_resource_id(vctx.client.networks, network, "network")
    net_obj = vctx.client.networks.get(net_key)

    view_key = _resolve_view_id(net_obj, view)
    view_obj = net_obj.dns_views.get(view_key)

    view_name = view_obj.get("name") or str(view_key)

    if not confirm_action(f"Delete DNS view '{view_name}' and all its zones?", yes=yes):
        typer.echo("Cancelled.")
        raise typer.Exit(0)

    net_obj.dns_views.delete(view_key)
    output_success(f"Deleted DNS view '{view_name}'", quiet=vctx.quiet)
