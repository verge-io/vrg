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
    help="LLDP neighbor discovery.",
    no_args_is_help=True,
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
