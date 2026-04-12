"""Cluster management commands."""

from __future__ import annotations

from typing import Annotated, Any

import typer

from verge_cli.columns import CLUSTER_COLUMNS, VSAN_STATUS_COLUMNS
from verge_cli.context import get_context
from verge_cli.errors import handle_errors
from verge_cli.multi import list_all_profiles
from verge_cli.output import output_result, output_success
from verge_cli.utils import confirm_action, resolve_resource_id

app = typer.Typer(
    name="cluster",
    help="Manage clusters.",
    no_args_is_help=True,
)


def _cluster_to_dict(cluster: Any) -> dict[str, Any]:
    """Convert a Cluster object to a dict for output."""
    # Use SDK properties for computed fields (total_ram_gb, ram_used_percent,
    # is_compute, is_storage, status) since .get() only accesses raw data.
    # Fall back to .get() for fields that may be on mock objects in tests.
    return {
        "$key": cluster.key,
        "name": cluster.name,
        "status": getattr(cluster, "status", cluster.get("status", "")),
        "total_nodes": cluster.get("total_nodes"),
        "online_nodes": cluster.get("online_nodes"),
        "total_ram_gb": getattr(cluster, "total_ram_gb", cluster.get("total_ram_gb")),
        "ram_used_percent": getattr(cluster, "ram_used_percent", cluster.get("ram_used_percent")),
        "total_cores": cluster.get("total_cores"),
        "running_machines": cluster.get("running_machines"),
        "is_compute": getattr(cluster, "is_compute", cluster.get("is_compute")),
        "is_storage": getattr(cluster, "is_storage", cluster.get("is_storage")),
    }


@app.command("list")
@handle_errors()
def cluster_list(
    ctx: typer.Context,
) -> None:
    """List all clusters."""
    if ctx.obj.get("all_profiles"):
        list_all_profiles(ctx, lambda c: c.clusters.list(), _cluster_to_dict, CLUSTER_COLUMNS)
        return
    vctx = get_context(ctx)

    clusters = vctx.client.clusters.list()
    data = [_cluster_to_dict(c) for c in clusters]

    output_result(
        data,
        output_format=vctx.output_format,
        query=vctx.query,
        columns=CLUSTER_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("get")
@handle_errors()
def cluster_get(
    ctx: typer.Context,
    cluster: Annotated[str, typer.Argument(help="Cluster name or key")],
) -> None:
    """Get details of a cluster."""
    vctx = get_context(ctx)

    key = resolve_resource_id(vctx.client.clusters, cluster, "Cluster")
    cluster_obj = vctx.client.clusters.get(key)

    output_result(
        _cluster_to_dict(cluster_obj),
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("create")
@handle_errors()
def cluster_create(
    ctx: typer.Context,
    name: Annotated[str, typer.Option("--name", "-n", help="Cluster name")],
    description: Annotated[
        str, typer.Option("--description", "-d", help="Cluster description")
    ] = "",
    enabled: Annotated[
        bool | None,
        typer.Option("--enabled/--no-enabled", help="Enable the cluster"),
    ] = None,
    compute: Annotated[
        bool | None,
        typer.Option("--compute/--no-compute", help="Mark as compute cluster"),
    ] = None,
) -> None:
    """Create a new cluster."""
    vctx = get_context(ctx)

    kwargs: dict[str, Any] = {
        "name": name,
        "description": description,
    }
    if enabled is not None:
        kwargs["enabled"] = enabled
    if compute is not None:
        kwargs["compute"] = compute

    cluster_obj = vctx.client.clusters.create(**kwargs)

    output_success(
        f"Created cluster '{cluster_obj.name}' (key: {cluster_obj.key})",
        quiet=vctx.quiet,
    )

    output_result(
        _cluster_to_dict(cluster_obj),
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("update")
@handle_errors()
def cluster_update(
    ctx: typer.Context,
    cluster: Annotated[str, typer.Argument(help="Cluster name or key")],
    name: Annotated[str | None, typer.Option("--name", "-n", help="New cluster name")] = None,
    description: Annotated[
        str | None,
        typer.Option("--description", "-d", help="Cluster description"),
    ] = None,
    enabled: Annotated[
        bool | None,
        typer.Option("--enabled/--no-enabled", help="Enable/disable the cluster"),
    ] = None,
    compute: Annotated[
        bool | None,
        typer.Option("--compute/--no-compute", help="Mark as compute cluster"),
    ] = None,
) -> None:
    """Update a cluster."""
    vctx = get_context(ctx)

    key = resolve_resource_id(vctx.client.clusters, cluster, "Cluster")

    updates: dict[str, Any] = {}
    if name is not None:
        updates["name"] = name
    if description is not None:
        updates["description"] = description
    if enabled is not None:
        updates["enabled"] = enabled
    if compute is not None:
        updates["compute"] = compute

    if not updates:
        typer.echo("No updates specified.", err=True)
        raise typer.Exit(2)

    cluster_obj = vctx.client.clusters.update(key, **updates)

    output_success(f"Updated cluster '{cluster_obj.name}'", quiet=vctx.quiet)

    output_result(
        _cluster_to_dict(cluster_obj),
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("delete")
@handle_errors()
def cluster_delete(
    ctx: typer.Context,
    cluster: Annotated[str, typer.Argument(help="Cluster name or key")],
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation")] = False,
) -> None:
    """Delete a cluster."""
    vctx = get_context(ctx)

    key = resolve_resource_id(vctx.client.clusters, cluster, "Cluster")
    cluster_obj = vctx.client.clusters.get(key)

    if not confirm_action(f"Delete cluster '{cluster_obj.name}'?", yes=yes):
        typer.echo("Cancelled.")
        raise typer.Exit(0)

    vctx.client.clusters.delete(key)
    output_success(f"Deleted cluster '{cluster_obj.name}'", quiet=vctx.quiet)


def _vsan_status_to_dict(status: Any) -> dict[str, Any]:
    """Convert a VSANStatus object to a dict for output."""
    return {
        "cluster_name": status.cluster_name,
        "health_status": status.health_status,
        "total_nodes": status.total_nodes,
        "online_nodes": status.online_nodes,
        "used_ram_gb": status.used_ram_gb,
        "online_ram_gb": status.online_ram_gb,
        "ram_used_percent": status.ram_used_percent,
        "total_cores": status.total_cores,
        "online_cores": status.online_cores,
        "used_cores": status.used_cores,
        "core_used_percent": status.core_used_percent,
        "running_machines": status.running_machines,
        "tiers": status.tiers,
    }


@app.command("vsan-status")
@handle_errors()
def cluster_vsan_status(
    ctx: typer.Context,
    name: Annotated[
        str | None,
        typer.Option("--name", "-n", help="Cluster name to query"),
    ] = None,
    include_tiers: Annotated[
        bool,
        typer.Option("--include-tiers", help="Include per-tier status"),
    ] = False,
) -> None:
    """Show vSAN status for clusters."""
    vctx = get_context(ctx)

    kwargs: dict[str, Any] = {}
    if name is not None:
        kwargs["cluster_name"] = name
    if include_tiers:
        kwargs["include_tiers"] = True

    statuses = vctx.client.clusters.vsan_status(**kwargs)
    data = [_vsan_status_to_dict(s) for s in statuses]

    output_result(
        data,
        output_format=vctx.output_format,
        query=vctx.query,
        columns=VSAN_STATUS_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )
