"""Node management commands."""

from __future__ import annotations

from typing import Annotated, Any

import typer

from verge_cli.columns import NODE_COLUMNS, NODE_GPU_COLUMNS, NODE_PCI_COLUMNS
from verge_cli.commands import node_query
from verge_cli.context import get_context
from verge_cli.errors import handle_errors
from verge_cli.multi import list_all_profiles
from verge_cli.output import output_result, output_success
from verge_cli.utils import confirm_action, resolve_resource_id

app = typer.Typer(
    name="node",
    help="Manage nodes.",
    no_args_is_help=True,
)

app.add_typer(node_query.app, name="query")


def _node_to_dict(node: Any) -> dict[str, Any]:
    """Convert a Node object to a dict for output.

    Uses getattr() for SDK computed properties (ram_gb, is_physical,
    vergeos_version, status, cluster_name) which are @property accessors
    on the Node model, not available via .get().
    Falls back to .get() for raw data fields.
    """
    return {
        "$key": node.key,
        "name": node.name,
        "status": getattr(node, "status", node.get("status", "")),
        "cluster_name": getattr(node, "cluster_name", node.get("cluster_name", "")),
        "ram_gb": getattr(node, "ram_gb", node.get("ram_gb")),
        "cores": node.get("cores"),
        "cpu_usage": getattr(node, "cpu_usage", node.get("cpu_usage")),
        "is_physical": getattr(node, "is_physical", node.get("is_physical")),
        "model": node.get("model", ""),
        "cpu": node.get("cpu", ""),
        "core_temp": getattr(node, "core_temp", node.get("core_temp")),
        "vergeos_version": getattr(node, "vergeos_version", node.get("vergeos_version", "")),
    }


def _pci_to_dict(pci: Any) -> dict[str, Any]:
    """Convert a NodePCIDevice SDK object to a dict for output."""
    return {
        "$key": pci.key,
        "name": getattr(pci, "name", pci.get("name", "")),
        "slot": pci.get("slot", ""),
        "vendor": pci.get("vendor", ""),
        "device": pci.get("device", ""),
        "driver": pci.get("driver", ""),
        "class_display": pci.get("class_display", pci.get("class", "")),
    }


def _gpu_to_dict(gpu: Any) -> dict[str, Any]:
    """Convert a NodeGpu SDK object to a dict for output."""
    return {
        "$key": gpu.key,
        "name": getattr(gpu, "name", gpu.get("name", "")),
        "slot": gpu.get("slot", ""),
        "vendor": gpu.get("vendor", ""),
        "device": gpu.get("device", ""),
        "driver": gpu.get("driver", ""),
        "max_instances": gpu.get("max_instances"),
    }


@app.command("list")
@handle_errors()
def node_list(
    ctx: typer.Context,
    cluster: Annotated[
        str | None,
        typer.Option("--cluster", "-c", help="Filter by cluster name"),
    ] = None,
) -> None:
    """List all nodes."""
    if ctx.obj.get("all_profiles"):
        list_all_profiles(ctx, lambda c: c.nodes.list(), _node_to_dict, NODE_COLUMNS)
        return
    vctx = get_context(ctx)

    kwargs: dict[str, Any] = {}
    if cluster is not None:
        kwargs["cluster"] = cluster

    nodes = vctx.client.nodes.list(**kwargs)
    data = [_node_to_dict(n) for n in nodes]

    output_result(
        data,
        output_format=vctx.output_format,
        query=vctx.query,
        columns=NODE_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("get")
@handle_errors()
def node_get(
    ctx: typer.Context,
    node: Annotated[str, typer.Argument(help="Node name or key")],
) -> None:
    """Get details of a node."""
    vctx = get_context(ctx)

    key = resolve_resource_id(vctx.client.nodes, node, "Node")
    node_obj = vctx.client.nodes.get(key)

    output_result(
        _node_to_dict(node_obj),
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("maintenance")
@handle_errors()
def node_maintenance(
    ctx: typer.Context,
    node: Annotated[str, typer.Argument(help="Node name or key")],
    enable: Annotated[
        bool,
        typer.Option("--enable", help="Enable maintenance mode"),
    ] = False,
    disable: Annotated[
        bool,
        typer.Option("--disable", help="Disable maintenance mode"),
    ] = False,
) -> None:
    """Enable or disable maintenance mode on a node."""
    if enable == disable:
        # Both True (impossible via CLI, but defensive) or both False
        typer.echo("Error: Specify exactly one of --enable or --disable.", err=True)
        raise typer.Exit(2)

    vctx = get_context(ctx)
    key = resolve_resource_id(vctx.client.nodes, node, "Node")

    if enable:
        vctx.client.nodes.enable_maintenance(key)
        output_success(f"Enabled maintenance mode on node '{node}'", quiet=vctx.quiet)
    else:
        vctx.client.nodes.disable_maintenance(key)
        output_success(f"Disabled maintenance mode on node '{node}'", quiet=vctx.quiet)


@app.command("restart")
@handle_errors()
def node_restart(
    ctx: typer.Context,
    node: Annotated[str, typer.Argument(help="Node name or key")],
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation")] = False,
) -> None:
    """Restart a node."""
    vctx = get_context(ctx)

    key = resolve_resource_id(vctx.client.nodes, node, "Node")

    if not confirm_action(f"Restart node '{node}'?", yes=yes):
        typer.echo("Cancelled.")
        raise typer.Exit(0)

    vctx.client.nodes.restart(key)
    output_success(f"Restarting node '{node}'", quiet=vctx.quiet)


@app.command("pci-list")
@handle_errors()
def node_pci_list(
    ctx: typer.Context,
    node: Annotated[str, typer.Argument(help="Node name or key")],
) -> None:
    """List PCI devices on a node."""
    vctx = get_context(ctx)
    key = resolve_resource_id(vctx.client.nodes, node, "Node")
    devices = vctx.client.nodes.pci_devices(key).list()
    data = [_pci_to_dict(d) for d in devices]
    output_result(
        data,
        output_format=vctx.output_format,
        query=vctx.query,
        columns=NODE_PCI_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("gpu-list")
@handle_errors()
def node_gpu_list(
    ctx: typer.Context,
    node: Annotated[str, typer.Argument(help="Node name or key")],
) -> None:
    """List GPU devices on a node."""
    vctx = get_context(ctx)
    key = resolve_resource_id(vctx.client.nodes, node, "Node")
    gpus = vctx.client.nodes.gpus(key).list()
    data = [_gpu_to_dict(g) for g in gpus]
    output_result(
        data,
        output_format=vctx.output_format,
        query=vctx.query,
        columns=NODE_GPU_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("stats")
@handle_errors()
def node_stats(
    ctx: typer.Context,
    node: Annotated[str, typer.Argument(help="Node name or key")],
) -> None:
    """Display statistics for a node."""
    vctx = get_context(ctx)
    key = resolve_resource_id(vctx.client.nodes, node, "Node")
    node_obj = vctx.client.nodes.get(key)
    stats = node_obj.stats.get()
    output_result(
        stats,
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )
