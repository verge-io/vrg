"""Node LLDP neighbor commands for Verge CLI."""

from __future__ import annotations

from typing import Annotated, Any

import typer

from verge_cli.columns import LLDP_NEIGHBOR_COLUMNS
from verge_cli.context import get_context
from verge_cli.errors import handle_errors
from verge_cli.output import output_result
from verge_cli.utils import resolve_resource_id

app = typer.Typer(
    name="lldp",
    help=(
        "Inspect LLDP neighbors discovered on a node's physical NICs — the"
        " switch port, chassis, and device each uplink is cabled into.\n\n"
        "Link Layer Discovery Protocol (LLDP) is a vendor-neutral protocol"
        " that switches and endpoints use to advertise their identity and"
        " capabilities over directly attached links. VergeOS nodes listen"
        " for these advertisements and record one neighbor entry per"
        " physical NIC that has an active LLDP peer.\n\n"
        "Use this to answer questions like: *Which switch port is node1's"
        " NIC 2 plugged into? Are both uplinks landing on different"
        " switches for redundancy? Why does this NIC show `no_path` — is"
        " it cabled to the wrong fabric?*\n\n"
        "LLDP advertisement is governed by the per-node `lldp` operational"
        " setting (default: `auto`). If a node has LLDP disabled or the"
        " neighboring switch does not send LLDP, the neighbor table will"
        " be empty. For i40e-driver NICs the OS deliberately stops LLDP"
        " on the NIC firmware to prevent LACP interference — the kernel"
        " still sees neighbors from userspace.\n\n"
        "---\n\n"
        "**Examples:**\n\n"
        "    # All LLDP neighbors visible on node1\n"
        "    vrg node lldp list node1\n\n"
        "    # Only the neighbor on NIC key 2\n"
        "    vrg node lldp list node1 --nic 2\n\n"
        "    # JSON for scripts and agents\n"
        "    vrg -o json node lldp list node1\n\n"
        '    # Find NICs whose upstream switch name contains "core"\n'
        "    vrg -o json node lldp list node1 | jq '.[] | select(.chassis_name | contains(\"core\"))'\n\n"
        "---\n\n"
        "**Notes:**\n\n"
        "Node is resolved by name or numeric key. Ambiguous names exit 7"
        " — pass the numeric key to disambiguate.\n\n"
        "Columns: `nic` (node-local NIC key), `chassis_name` (peer device"
        " hostname), `port_id` (peer switch port), `via` (protocol:"
        " `LLDP`, `CDP`, etc.), `age` (seconds since last advertisement),"
        " `rid` (remote chassis ID, wide/`-o wide` only). All are safe"
        " `--query` targets.\n\n"
        "Read-only. Empty output means either LLDP is disabled for this"
        " node or no peers are advertising on its NICs — check the node's"
        " `lldp` setting and confirm the upstream switch has LLDP enabled."
    ),
    no_args_is_help=True,
    rich_markup_mode="markdown",
)


def _neighbor_to_dict(neighbor: Any) -> dict[str, Any]:
    """Convert an LLDP neighbor to output dict."""
    return {
        "$key": neighbor.key,
        "nic": getattr(neighbor, "nic_key", neighbor.get("nic", "")),
        "chassis_name": getattr(neighbor, "chassis_name", None) or "",
        "port_id": getattr(neighbor, "port_id", None) or "",
        "via": getattr(neighbor, "via", neighbor.get("via", "")),
        "age": getattr(neighbor, "age", neighbor.get("age", "")),
        "rid": getattr(neighbor, "remote_id", neighbor.get("rid", "")),
    }


@app.command("list")
@handle_errors()
def lldp_list(
    ctx: typer.Context,
    node: Annotated[str, typer.Argument(help="Node name or key")],
    nic: Annotated[
        int | None,
        typer.Option("--nic", help="Filter by NIC key."),
    ] = None,
) -> None:
    """List LLDP neighbors discovered on a node.

    Shows neighboring network devices discovered via LLDP protocol
    on the node's physical NICs.

    Examples:

        # Every peer visible on node1
        vrg node lldp list node1

        # Just the peer on NIC 2
        vrg node lldp list node1 --nic 2

        # JSON, filter to neighbors on "core" switches
        vrg -o json node lldp list node1 | jq '.[] | select(.chassis_name | contains("core"))'

    Empty output means LLDP is disabled on the node or no peers are
    advertising — check the node's `lldp` setting and confirm the upstream
    switch has LLDP enabled.
    """
    vctx = get_context(ctx)
    node_key = resolve_resource_id(vctx.client.nodes, node, "node")
    node_obj = vctx.client.nodes.get(node_key)

    if nic is not None:
        neighbors = node_obj.lldp_neighbors.list(filter=f"nic eq {nic}")
    else:
        neighbors = node_obj.lldp_neighbors.list()

    data = [_neighbor_to_dict(n) for n in neighbors]

    output_result(
        data,
        output_format=vctx.output_format,
        query=vctx.query,
        columns=LLDP_NEIGHBOR_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )
