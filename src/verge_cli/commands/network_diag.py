"""Network diagnostics commands for Verge CLI."""

from __future__ import annotations

from typing import Annotated, Any

import typer

from verge_cli.columns import (
    ADDRESS_COLUMNS,
    LEASE_COLUMNS,
    MONITOR_HISTORY_COLUMNS,
    MONITOR_QUALITY_COLUMNS,
)
from verge_cli.commands import network_dashboard
from verge_cli.context import get_context
from verge_cli.errors import handle_errors
from verge_cli.output import output_result
from verge_cli.utils import resolve_resource_id

app = typer.Typer(
    name="diag",
    help=(
        "Read-only diagnostic snapshots and traffic/quality telemetry for a"
        " vnet.\n\n"
        "Every VergeOS virtual network runs inside its own LXC container with"
        " `dnsmasq` providing DHCP/DNS, `nftables` enforcing firewall rules,"
        " and a background monitor sampling connectivity at **5-second**"
        " intervals (rolled up into 5-minute aggregates for long-term"
        " history). This command group surfaces that data without restarting"
        " or reconfiguring anything.\n\n"
        "Subcommands:\n\n"
        "- `leases` — active/reserved DHCP leases served by the vnet's"
        " dnsmasq.\n"
        "- `addresses` — IP/MAC/interface address table seen inside the"
        " vnet.\n"
        "- `stats` — cumulative bytes/packets/errors in and out.\n"
        "- `quality` — current monitoring sample (quality %, latency, packet"
        " loss).\n"
        "- `history` — timestamped quality history (short-term raw or"
        " long-term aggregated).\n"
        "- `dashboard` — network dashboard summary.\n\n"
        "Every subcommand supports `-o json` for machine-readable output and"
        " `--query` for JMESPath filtering. Networks are identified by name"
        " or numeric key.\n\n"
        "---\n\n"
        "**Examples:**\n\n"
        "    # DHCP leases currently held on an internal network (JSON)\n"
        "    vrg -o json network diag leases internal-prod\n\n"
        "    # Address table for a network\n"
        "    vrg network diag addresses internal-prod\n\n"
        "    # Cumulative traffic counters (bytes/packets in & out)\n"
        "    vrg network diag stats internal-prod\n\n"
        "    # Current connectivity quality sample\n"
        "    vrg network diag quality external-wan\n\n"
        "    # Last 50 short-term (raw, 5s) monitoring samples\n"
        "    vrg network diag history external-wan --limit 50\n\n"
        "    # Long-term aggregated history (5-minute rollups, longer"
        " retention)\n"
        "    vrg network diag history external-wan --long --limit 200\n\n"
        "    # Find the lease for a specific MAC (JSON + jq)\n"
        "    vrg -o json network diag leases internal-prod | jq"
        " '.[] | select(.mac == \"52:54:00:12:34:56\")'\n\n"
        "---\n\n"
        "**Notes:**\n\n"
        "These commands are **read-only snapshots** from the SDK"
        " diagnostics endpoints — they do not execute interactive tools"
        " (ping, traceroute, tcpdump, nmap) that the web UI exposes. If you"
        " need those, drive them via the network's Diagnostics page or a"
        " custom task.\n\n"
        "Monitoring quality/history is only populated for networks with"
        " monitoring enabled. External networks and networks with upstream"
        " gateways generally produce the most useful quality data;"
        " internal-only networks may report zeros.\n\n"
        "DHCP leases reflect what **dnsmasq** currently has in its lease"
        " file. Static entries configured via `vrg network host` also show"
        " up here once a client requests them.\n\n"
        "Ambiguous network names return **exit code 7** (multiple matches);"
        " missing networks return **exit code 6** (not found)."
    ),
    no_args_is_help=True,
    rich_markup_mode="markdown",
)

app.add_typer(network_dashboard.app, name="dashboard")


def _item_to_dict(item: Any) -> dict[str, Any]:
    """Convert a diagnostics item to a dictionary for output.

    Handles both dict and object-like responses from the SDK.

    Args:
        item: Item from SDK (dict or object).

    Returns:
        Dictionary representation.
    """
    if isinstance(item, dict):
        return dict(item)

    # Handle object-like response with .get() method
    if hasattr(item, "get"):
        result: dict[str, Any] = dict(item)
        return result

    # Handle object with __dict__
    if hasattr(item, "__dict__"):
        result = dict(vars(item))
        return result

    return {"value": str(item)}


def _stats_to_dict(stats: Any) -> dict[str, Any]:
    """Convert network statistics to a dictionary for output.

    Handles both dict and object-like responses from the SDK.

    Args:
        stats: Statistics from SDK (dict or object).

    Returns:
        Dictionary representation.
    """
    if isinstance(stats, dict):
        return dict(stats)

    # Handle MagicMock or object with .get() method
    if hasattr(stats, "get"):
        # Try common stat keys
        stat_keys = [
            "bytes_in",
            "bytes_out",
            "packets_in",
            "packets_out",
            "errors_in",
            "errors_out",
            "rx_bytes",
            "tx_bytes",
            "rx_packets",
            "tx_packets",
        ]
        result: dict[str, Any] = {}
        for key in stat_keys:
            value = stats.get(key)
            if value is not None:
                result[key] = value
        return result if result else {"data": str(stats)}

    # Handle object with __dict__
    if hasattr(stats, "__dict__"):
        result = dict(vars(stats))
        return result

    return {"data": str(stats)}


@app.command("leases")
@handle_errors()
def diag_leases(
    ctx: typer.Context,
    network: Annotated[str, typer.Argument(help="Network name or key")],
) -> None:
    """Show DHCP leases for a network.

    Displays active and reserved DHCP leases including MAC address,
    IP address, hostname, and expiration time.

    Useful for troubleshooting DHCP issues or finding device IPs.
    """
    vctx = get_context(ctx)

    net_key = resolve_resource_id(vctx.client.networks, network, "network")
    net_obj = vctx.client.networks.get(net_key)

    result = net_obj.diagnostics(diagnostic_type="dhcp_leases")

    # SDK returns a dict with dhcp_leases key containing the actual leases
    if isinstance(result, dict) and "dhcp_leases" in result:
        leases = result["dhcp_leases"]
    else:
        leases = result

    data = [_item_to_dict(lease) for lease in leases]

    output_result(
        data,
        output_format=vctx.output_format,
        query=vctx.query,
        columns=LEASE_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("addresses")
@handle_errors()
def diag_addresses(
    ctx: typer.Context,
    network: Annotated[str, typer.Argument(help="Network name or key")],
) -> None:
    """Show all network addresses.

    Displays the address table for the network including IP addresses,
    MAC addresses, interfaces, and address types.

    Useful for viewing what devices are connected to the network.
    """
    vctx = get_context(ctx)

    net_key = resolve_resource_id(vctx.client.networks, network, "network")
    net_obj = vctx.client.networks.get(net_key)

    result = net_obj.diagnostics(diagnostic_type="addresses")

    # SDK returns a dict with addresses key containing the actual addresses
    if isinstance(result, dict) and "addresses" in result:
        addresses = result["addresses"]
    else:
        addresses = result

    data = [_item_to_dict(addr) for addr in addresses]

    output_result(
        data,
        output_format=vctx.output_format,
        query=vctx.query,
        columns=ADDRESS_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("stats")
@handle_errors()
def diag_stats(
    ctx: typer.Context,
    network: Annotated[str, typer.Argument(help="Network name or key")],
) -> None:
    """Show network traffic statistics.

    Displays traffic statistics including bytes and packets
    transmitted and received, as well as error counts.

    Useful for monitoring network performance and identifying issues.
    """
    vctx = get_context(ctx)

    net_key = resolve_resource_id(vctx.client.networks, network, "network")
    net_obj = vctx.client.networks.get(net_key)

    stats = net_obj.statistics()
    data = _stats_to_dict(stats)

    output_result(
        data,
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


def _monitor_stats_to_dict(stats: Any) -> dict[str, Any]:
    """Convert NetworkMonitorStats to output dict."""
    return {
        "quality": getattr(stats, "quality", stats.get("quality", 0)),
        "latency_avg_ms": getattr(stats, "latency_avg_ms", 0),
        "latency_peak_ms": getattr(stats, "latency_peak_ms", 0),
        "sent": getattr(stats, "sent", stats.get("sent", 0)),
        "dropped": getattr(stats, "dropped", stats.get("dropped", 0)),
        "dropped_pct": getattr(stats, "dropped_pct", stats.get("dropped_pct", 0)),
        "duplicates": getattr(stats, "duplicates", stats.get("duplicates", 0)),
        "bad_checksums": getattr(stats, "bad_checksums", stats.get("bad_checksums", 0)),
        "bad_data": getattr(stats, "bad_data", stats.get("bad_data", 0)),
    }


def _monitor_history_to_dict(point: Any) -> dict[str, Any]:
    """Convert NetworkMonitorStatsHistory to output dict."""
    ts = getattr(point, "timestamp", None)
    return {
        "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S") if ts else str(point.get("timestamp", "")),
        "quality": getattr(point, "quality", point.get("quality", 0)),
        "latency_avg_ms": getattr(point, "latency_avg_ms", 0),
        "latency_peak_ms": getattr(point, "latency_peak_ms", 0),
        "dropped": getattr(point, "dropped", point.get("dropped", 0)),
        "sent": getattr(point, "sent", point.get("sent", 0)),
    }


@app.command("quality")
@handle_errors()
def diag_quality(
    ctx: typer.Context,
    network: Annotated[str, typer.Argument(help="Network name or key")],
) -> None:
    """Show current network quality metrics.

    Displays the most recent monitoring sample including quality
    percentage, latency, packet loss, and error counts.
    """
    vctx = get_context(ctx)

    net_key = resolve_resource_id(vctx.client.networks, network, "network")
    net_obj = vctx.client.networks.get(net_key)

    stats = net_obj.stats.get()
    data = _monitor_stats_to_dict(stats)

    output_result(
        data,
        output_format=vctx.output_format,
        query=vctx.query,
        columns=MONITOR_QUALITY_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("history")
@handle_errors()
def diag_history(
    ctx: typer.Context,
    network: Annotated[str, typer.Argument(help="Network name or key")],
    limit: Annotated[
        int,
        typer.Option("--limit", "-l", help="Maximum number of history records."),
    ] = 20,
    long: Annotated[
        bool,
        typer.Option("--long", help="Use long-term history (aggregated, longer retention)."),
    ] = False,
) -> None:
    """Show network monitoring history.

    Displays timestamped quality, latency, and packet loss data.
    Use --long for aggregated long-term history.
    """
    vctx = get_context(ctx)

    net_key = resolve_resource_id(vctx.client.networks, network, "network")
    net_obj = vctx.client.networks.get(net_key)

    if long:
        history = net_obj.stats.history_long(limit=limit)
    else:
        history = net_obj.stats.history_short(limit=limit)

    data = [_monitor_history_to_dict(point) for point in history]

    output_result(
        data,
        output_format=vctx.output_format,
        query=vctx.query,
        columns=MONITOR_HISTORY_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )
