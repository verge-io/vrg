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
    help=(
        "Manage VergeOS clusters — the top-level logical grouping of"
        " `node`s that defines compute scheduling, storage pooling, and"
        " availability boundaries.\n\n"
        "A **cluster** is the unit of resource pooling. Each cluster"
        " aggregates CPU, RAM, and (on hyperconverged deployments) vSAN"
        " storage tiers contributed by its member nodes. Cluster-level"
        " settings (CPU type, temperature thresholds, power policy,"
        " overcommit, scaling governor) flow down to every member node"
        " unless a node defines its own override. Failover, live"
        " migration, and vSAN redundancy all operate within cluster"
        " boundaries.\n\n"
        "The first two nodes installed are typically **controllers** that"
        " host the management plane (API, UI, PXE); additional nodes join"
        " as compute or hyperconverged members and expand capacity. See"
        " `vrg node --help` for node-level operations.\n\n"
        "---\n\n"
        "**Examples:**\n\n"
        "    # List clusters with aggregate capacity and node counts\n"
        "    vrg cluster list\n\n"
        "    # Full cluster details as JSON\n"
        "    vrg -o json cluster get default\n\n"
        "    # vSAN health and capacity across clusters\n"
        "    vrg cluster vsan-status\n"
        "    vrg cluster vsan-status --name default --include-tiers\n\n"
        "    # Filter unhealthy vSAN status with jq\n"
        "    vrg -o json cluster vsan-status | jq '.[] | select(.health_status != \"healthy\")'\n\n"
        "    # Create a new cluster (admin)\n"
        "    vrg cluster create --name edge-west --compute\n\n"
        "    # Toggle compute scheduling on an existing cluster\n"
        "    vrg cluster update default --no-compute\n\n"
        "    # Delete a cluster (must be empty)\n"
        "    vrg cluster delete edge-west -y\n\n"
        "---\n\n"
        "**Notes:**\n\n"
        "Clusters are addressed by name or numeric key (`$key`). When a"
        " name matches multiple clusters, vrg prints all matches and"
        " exits with code 7 — use the numeric key to disambiguate.\n\n"
        "Cluster status aggregates the state of every member node:"
        " `online` (full capacity), `reduced` (one or more nodes"
        " offline), `noredundant` (vSAN redundancy lost — data at risk),"
        " `maintenance`, `updating`, `insufficient` (too few nodes to"
        " operate), or `error`. Anything other than `online` warrants"
        " investigation.\n\n"
        "The `storage` flag on a cluster is read-only — it reflects"
        " whether any member node contributes vSAN storage tiers, not a"
        " setting you toggle directly. Adjust storage participation by"
        " changing node types, not cluster flags.\n\n"
        "Use `-o json` (or `-o wide` for extra columns) for"
        " machine-readable output. Useful fields for `--query`:"
        " `status`, `total_nodes`, `online_nodes`, `ram_used_percent`,"
        " `running_machines`, `is_compute`, `is_storage`. For"
        " `vsan-status`: `health_status`, `core_used_percent`,"
        " `online_ram_gb`, `tiers`."
    ),
    no_args_is_help=True,
    rich_markup_mode="markdown",
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
    """List all clusters.

    Examples:

        vrg cluster list
        vrg -o json cluster list
        vrg -o json cluster list | jq '.[] | select(.status != "online")'

    Use `-A` / `--all-profiles` to fan out across every configured profile.
    """
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
    """Get details of a cluster.

    Examples:

        vrg cluster get default
        vrg -o json cluster get default
        vrg -o json cluster get 1 --query "{nodes: total_nodes, ram: total_ram_gb}"

    Resolves by name or numeric key. Ambiguous names exit 7.
    """
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
    """Create a new cluster.

    Examples:

        # Compute cluster for edge workloads
        vrg cluster create --name edge-west --compute

        # Disabled by default — enable later after adding nodes
        vrg cluster create --name tier-2 --description "Backup cluster" --no-enabled

    Creates an empty cluster definition. Member nodes are added by
    installing/joining them to the cluster; the CLI does not provision
    nodes directly. Storage participation (`is_storage`) is derived from
    member node types and cannot be set here.
    """
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
    """Update a cluster.

    Examples:

        # Rename
        vrg cluster update default --name primary

        # Stop scheduling new VMs on this cluster
        vrg cluster update edge-west --no-compute

        # Update description
        vrg cluster update default -d "Primary production cluster"

    At least one field must be specified (exits 2 otherwise). Disabling
    compute stops new VM placement; existing VMs continue running.
    """
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
    """Delete a cluster.

    Examples:

        vrg cluster delete edge-west
        vrg cluster delete edge-west -y

    Destructive and irreversible. The cluster must be empty — remove or
    reassign member nodes first, otherwise the API rejects the delete.
    """
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
    """Show vSAN status for clusters.

    Examples:

        # Health + capacity for every cluster
        vrg cluster vsan-status

        # Narrow to one cluster, include per-tier breakdown
        vrg cluster vsan-status --name default --include-tiers

        # Flag clusters whose vSAN is not healthy
        vrg -o json cluster vsan-status | jq '.[] | select(.health_status != "healthy")'

    `health_status` reflects vSAN data redundancy state. Anything other
    than `healthy` warrants investigation — `reduced` or `at_risk` means
    replica counts have dropped and data is vulnerable until rebuild
    completes.
    """
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
