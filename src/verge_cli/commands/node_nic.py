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
    help="NIC monitoring and statistics.",
    no_args_is_help=True,
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
    """Show NIC traffic statistics for a node."""
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
    """Show NIC link status for a node."""
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
    """Show NIC fabric status for a node."""
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
