"""Node NIC monitoring commands for Verge CLI."""

from __future__ import annotations

from typing import Annotated, Any

import typer
from pyvergeos.exceptions import NotFoundError

from verge_cli.columns import NIC_FABRIC_COLUMNS, NIC_STATS_COLUMNS, NIC_STATUS_COLUMNS
from verge_cli.context import get_context
from verge_cli.errors import handle_errors
from verge_cli.output import output_result
from verge_cli.utils import resolve_resource_id

app = typer.Typer(
    name="nic",
    help=(
        "Inspect physical NICs on a node — live traffic stats, link state,"
        " and vSAN fabric reachability.\n\n"
        "Every VergeOS node enumerates its physical NICs at boot from"
        " `/boot/active/network-config` and exposes three live views per"
        " NIC:\n\n"
        "- **stats** — packets/second and bits/second counters (RX and TX),"
        " plus cumulative packet and byte totals. Useful for spotting"
        " hot NICs or idle uplinks.\n"
        "- **status** — link state reported by the kernel: up/down, speed,"
        " and duplex. First thing to check when a node looks isolated.\n"
        "- **fabric** — vSAN fabric reachability status: `confirmed` means"
        " the NIC has a working path across the core switch fabric,"
        " `degraded` means partial connectivity, `no_path` means the NIC"
        " is present but cannot reach peers. Refresh with"
        " `refresh_fabric_status` on the parent node.\n\n"
        "These commands are read-only. All three take a **node** (name or"
        " key) as the first argument and an optional `--nic <key>` to"
        " restrict output to a single NIC.\n\n"
        "---\n\n"
        "**Examples:**\n\n"
        "    # Traffic counters for every NIC on node1\n"
        "    vrg node nic stats node1\n\n"
        "    # Just one NIC (by its numeric key within the node)\n"
        "    vrg node nic stats node1 --nic 2\n\n"
        "    # Link up/down and negotiated speed\n"
        "    vrg node nic status node1\n\n"
        "    # Fabric reachability (vSAN path health)\n"
        "    vrg node nic fabric node1\n\n"
        "    # JSON output for scripting or agent parsing\n"
        "    vrg -o json node nic stats node1\n"
        "    vrg -o json node nic fabric node1 | jq '.[] | select(.status != \"confirmed\")'\n\n"
        "---\n\n"
        "**Notes:**\n\n"
        "The node argument is resolved by name or numeric key. If a name"
        " matches multiple nodes, vrg prints all matches and exits with"
        " code 7 — use the numeric key to disambiguate.\n\n"
        "NICs that have no cached stats/status/fabric data are silently"
        " skipped, so an empty result set means either the node has no"
        " NICs or none have reported in yet.\n\n"
        "Use `-o json` (or `-o wide` for extra stats columns) for"
        " machine-readable output. Useful fields for `--query`:"
        " `parent_nic`, `status`, `speed`, `txpps`, `rxpps`, `txbps`,"
        " `rxbps`."
    ),
    no_args_is_help=True,
    rich_markup_mode="markdown",
)


def _get_node_nics(vctx: Any, node: str, nic: int | None = None) -> list[Any]:
    """Resolve node and return its NICs (all or filtered by key)."""
    node_key = resolve_resource_id(vctx.client.nodes, node, "node")
    node_obj = vctx.client.nodes.get(node_key)

    if nic is not None:
        return [node_obj.nics.get(key=nic)]

    return list(node_obj.nics.list())


@app.command("stats")
@handle_errors()
def nic_stats(
    ctx: typer.Context,
    node: Annotated[str, typer.Argument(help="Node name or key")],
    nic: Annotated[
        int | None,
        typer.Option("--nic", help="Show only this NIC (by key)."),
    ] = None,
) -> None:
    """Show NIC traffic statistics for a node.

    Examples:

        # Packet and byte counters for every NIC on node1
        vrg node nic stats node1

        # Drill into one NIC by its node-local key
        vrg node nic stats node1 --nic 2

        # Find hot NICs (> 100k pps out)
        vrg -o json node nic stats node1 | jq '.[] | select(.txpps > 100000)'

    Read-only. NICs with no cached stats are skipped silently.
    """
    vctx = get_context(ctx)
    nics = _get_node_nics(vctx, node, nic)

    rows: list[dict[str, Any]] = []
    for n in nics:
        try:
            stats = n.nic_stats.get()
        except NotFoundError:
            continue
        rows.append(dict(stats))

    output_result(
        rows,
        output_format=vctx.output_format,
        query=vctx.query,
        columns=NIC_STATS_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("status")
@handle_errors()
def nic_status(
    ctx: typer.Context,
    node: Annotated[str, typer.Argument(help="Node name or key")],
    nic: Annotated[
        int | None,
        typer.Option("--nic", help="Show only this NIC (by key)."),
    ] = None,
) -> None:
    """Show NIC link status for a node.

    Examples:

        vrg node nic status node1
        vrg node nic status node1 --nic 2
        vrg -o json node nic status node1 | jq '.[] | select(.status == "down")'

    Reports kernel-level link state (up/down), negotiated speed, and
    duplex. First check when a node looks isolated.
    """
    vctx = get_context(ctx)
    nics = _get_node_nics(vctx, node, nic)

    rows: list[dict[str, Any]] = []
    for n in nics:
        try:
            status = n.link_status.get()
        except NotFoundError:
            continue
        rows.append(dict(status))

    output_result(
        rows,
        output_format=vctx.output_format,
        query=vctx.query,
        columns=NIC_STATUS_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("fabric")
@handle_errors()
def nic_fabric(
    ctx: typer.Context,
    node: Annotated[str, typer.Argument(help="Node name or key")],
    nic: Annotated[
        int | None,
        typer.Option("--nic", help="Show only this NIC (by key)."),
    ] = None,
) -> None:
    """Show NIC fabric status for a node.

    Examples:

        vrg node nic fabric node1
        vrg node nic fabric node1 --nic 2
        vrg -o json node nic fabric node1 | jq '.[] | select(.status != "confirmed")'

    Reports vSAN fabric reachability per NIC: `confirmed` (full path),
    `degraded` (partial), or `no_path` (isolated from peers). Combine
    with `vrg node lldp list` to figure out which uplink is cabled wrong.
    """
    vctx = get_context(ctx)
    nics = _get_node_nics(vctx, node, nic)

    rows: list[dict[str, Any]] = []
    for n in nics:
        try:
            fabric = n.fabric_status.get()
        except NotFoundError:
            continue
        rows.append(dict(fabric))

    output_result(
        rows,
        output_format=vctx.output_format,
        query=vctx.query,
        columns=NIC_FABRIC_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )
