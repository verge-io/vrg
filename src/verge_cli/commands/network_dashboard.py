"""Network dashboard and VPN status commands."""

from __future__ import annotations

from typing import Annotated, Any

import typer

from verge_cli.columns import BOOL_STYLES, ColumnDef, format_bool_yn
from verge_cli.context import get_context
from verge_cli.errors import handle_errors
from verge_cli.output import output_result
from verge_cli.utils import resolve_resource_id

app = typer.Typer(
    name="dashboard",
    help=(
        "Aggregate network dashboard + VPN tunnel status (IPSec,"
        " WireGuard).\n\n"
        "`overview` returns the cluster-wide network dashboard payload"
        " (same data the UI shows on the Networks dashboard). The"
        " `ipsec-status` and `wireguard-status` subcommands drill into a"
        " single vnet's active VPN connections and peer handshake state,"
        " respectively — useful for verifying tunnels after config changes"
        " or when troubleshooting disconnects.\n\n"
        "All subcommands support `-o json` for machine-readable output.\n\n"
        "---\n\n"
        "**Examples:**\n\n"
        "    # Cluster-wide network dashboard summary\n"
        "    vrg -o json network diag dashboard overview\n\n"
        "    # Active IPSec connections on a specific vnet\n"
        "    vrg network diag dashboard ipsec-status site-vpn\n\n"
        "    # WireGuard peer handshake state for a vnet\n"
        "    vrg -o json network diag dashboard wireguard-status remote-access\n\n"
        "---\n\n"
        "**Notes:**\n\n"
        "VPN status is read-only — configuration lives on the network"
        " itself (IPSec) or on WireGuard interfaces attached to the"
        " network. Ambiguous network names return **exit code 7** (multiple"
        " matches); missing networks return **exit code 6** (not found)."
    ),
    no_args_is_help=True,
    rich_markup_mode="markdown",
)

IPSEC_CONNECTION_COLUMNS: list[ColumnDef] = [
    ColumnDef("connection", header="Connection"),
    ColumnDef("status", header="Status"),
    ColumnDef("local_ip", header="Local IP"),
    ColumnDef("remote_ip", header="Remote IP"),
    ColumnDef("local_subnet", header="Local Subnet"),
    ColumnDef("remote_subnet", header="Remote Subnet"),
]

WIREGUARD_PEER_STATUS_COLUMNS: list[ColumnDef] = [
    ColumnDef("peer_key", header="Peer Key"),
    ColumnDef("endpoint", header="Endpoint"),
    ColumnDef("is_connected", header="Connected", format_fn=format_bool_yn, style_map=BOOL_STYLES),
    ColumnDef("latest_handshake", header="Last Handshake"),
    ColumnDef("transfer_rx", header="RX"),
    ColumnDef("transfer_tx", header="TX"),
    ColumnDef("allowed_ips", header="Allowed IPs"),
]


def _ipsec_to_dict(conn: Any) -> dict[str, Any]:
    """Convert an IPSecActiveConnection to a dict for output."""
    return {
        "connection": getattr(conn, "connection", conn.get("connection", "")),
        "status": getattr(conn, "status", conn.get("status", "")),
        "local_ip": conn.get("local_ip", ""),
        "remote_ip": conn.get("remote_ip", ""),
        "local_subnet": conn.get("local_subnet", ""),
        "remote_subnet": conn.get("remote_subnet", ""),
    }


def _wg_peer_to_dict(peer: Any) -> dict[str, Any]:
    """Convert a WireGuardPeerStatus to a dict for output."""
    return {
        "peer_key": getattr(peer, "peer_key", peer.get("peer_key")),
        "endpoint": getattr(peer, "endpoint", peer.get("endpoint", "")),
        "is_connected": getattr(peer, "is_connected", peer.get("is_connected", False)),
        "latest_handshake": getattr(peer, "latest_handshake", peer.get("latest_handshake", "")),
        "transfer_rx": peer.get("transfer_rx", ""),
        "transfer_tx": peer.get("transfer_tx", ""),
        "allowed_ips": getattr(peer, "allowed_ips", peer.get("allowed_ips", "")),
    }


@app.command("overview")
@handle_errors()
def dashboard_cmd(ctx: typer.Context) -> None:
    """Display network dashboard summary.

    **Examples:**

        vrg network diag dashboard overview
        vrg -o json network diag dashboard overview

    Cluster-wide aggregate — the same payload the web UI renders on
    the Networks dashboard. Use `-o json` for agent consumption.
    """
    vctx = get_context(ctx)
    dashboard = vctx.client.network_dashboard.get()
    output_result(
        dashboard,
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("ipsec-status")
@handle_errors()
def ipsec_status_cmd(
    ctx: typer.Context,
    network: Annotated[str, typer.Argument(help="Network name or key")],
) -> None:
    """Show IPSec active connections for a network.

    **Examples:**

        vrg network diag dashboard ipsec-status site-vpn
        vrg -o json network diag dashboard ipsec-status site-vpn

    Lists currently-established IPSec tunnels with local/remote
    addresses and subnets. Read-only — to change config, update
    the network's IPSec settings.
    """
    vctx = get_context(ctx)
    net_key = resolve_resource_id(vctx.client.networks, network, "Network")
    net_obj = vctx.client.networks.get(net_key)
    connections = net_obj.ipsec_connections.list()
    data = [_ipsec_to_dict(c) for c in connections]
    output_result(
        data,
        output_format=vctx.output_format,
        query=vctx.query,
        columns=IPSEC_CONNECTION_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("wireguard-status")
@handle_errors()
def wireguard_status_cmd(
    ctx: typer.Context,
    network: Annotated[str, typer.Argument(help="Network name or key")],
) -> None:
    """Show WireGuard peer status for a network.

    **Examples:**

        vrg network diag dashboard wireguard-status remote-access
        vrg -o json network diag dashboard wireguard-status remote-access

    Aggregates peer status across **every** WireGuard interface on
    the network. Each peer shows endpoint, last handshake time,
    connection state, and transfer counters.
    """
    vctx = get_context(ctx)
    net_key = resolve_resource_id(vctx.client.networks, network, "Network")
    net_obj = vctx.client.networks.get(net_key)

    interfaces = net_obj.wireguard.list()
    all_peers: list[dict[str, Any]] = []
    for iface in interfaces:
        peers = iface.peer_status.list()
        all_peers.extend(_wg_peer_to_dict(p) for p in peers)

    output_result(
        all_peers,
        output_format=vctx.output_format,
        query=vctx.query,
        columns=WIREGUARD_PEER_STATUS_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )
