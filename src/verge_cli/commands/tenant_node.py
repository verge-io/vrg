"""Tenant node (compute allocation) sub-resource commands."""

from __future__ import annotations

from typing import Annotated, Any

import typer

from verge_cli.columns import TENANT_NODE_COLUMNS
from verge_cli.context import get_context
from verge_cli.errors import handle_errors
from verge_cli.output import output_result, output_success
from verge_cli.utils import confirm_action, resolve_resource_id

app = typer.Typer(
    name="node",
    help=(
        "Manage compute nodes (virtual machines) that power a tenant.\n\n"
        "A **tenant node** is a virtual machine that provides the CPU and"
        " RAM for the nested VergeOS instance inside a tenant. A tenant's"
        " total compute capacity equals the sum across all its nodes, and"
        " each node has its own `cpu_cores` and `ram` allocation, cluster"
        " placement, and optional failover cluster. Defaults are 4 cores"
        " and 16 GB RAM; the minimums are 1 core and 2 GB. Before CPU or"
        " RAM changes take effect, the system validates that both the"
        " primary and (if configured) failover clusters have enough"
        " capacity, so over-commitment is rejected up front.\n\n"
        "Tenant nodes are referenced by **numeric key** or by node name."
        " Use `-o json` for machine-readable output; the `$key`, `name`,"
        " `cpu_cores`, `ram_gb`, `status`, and `cluster_name` fields are"
        " the most useful targets for `--query`. Name lookups that match"
        " multiple nodes exit with code 7 — pass a numeric key to"
        " disambiguate.\n\n"
        "---\n\n"
        "**Examples:**\n\n"
        "    # List compute nodes allocated to a tenant\n"
        "    vrg tenant node list acme-corp\n\n"
        "    # JSON output for agents\n"
        "    vrg -o json tenant node list acme-corp\n\n"
        "    # Inspect a specific tenant node by name\n"
        "    vrg tenant node get acme-corp acme-corp1\n\n"
        "    # Add a second node: 8 cores, 32 GB RAM on cluster key 2\n"
        "    vrg tenant node create acme-corp --cpu-cores 8 --ram-gb 32"
        " --cluster 2\n\n"
        "    # Scale an existing node up to 16 cores / 64 GB RAM\n"
        "    vrg tenant node update acme-corp acme-corp1 --cpu-cores 16"
        " --ram-gb 64\n\n"
        "    # Disable a node (stops new placements) without deleting it\n"
        "    vrg tenant node update acme-corp acme-corp2 --disabled\n\n"
        "    # Remove a tenant node\n"
        "    vrg tenant node delete acme-corp acme-corp2 -y\n\n"
        "---\n\n"
        "**Notes:**\n\n"
        "Prefer scaling an existing node up to the cluster's per-machine"
        " CPU/RAM limit before adding another node; once near the limit,"
        " balance capacity across nodes rather than leaving a tiny second"
        " node. The `--preferred-node` option is an advanced placement"
        " hint that can defeat built-in HA — leave it unset unless"
        " directed by support. CPU and RAM edits are accepted only if the"
        " cluster (and failover cluster, if configured) can satisfy the"
        " new allocation."
    ),
    no_args_is_help=True,
    rich_markup_mode="markdown",
)


def _get_tenant(ctx: typer.Context, tenant_identifier: str) -> tuple[Any, Any]:
    """Get the VergeContext and Tenant object."""
    vctx = get_context(ctx)
    key = resolve_resource_id(vctx.client.tenants, tenant_identifier, "Tenant")
    tenant_obj = vctx.client.tenants.get(key)
    return vctx, tenant_obj


def _tenant_node_to_dict(node: Any) -> dict[str, Any]:
    """Convert a Tenant Node object to a dict for output."""
    raw_ram = node.get("ram")
    ram_gb = round(raw_ram / 1024, 2) if isinstance(raw_ram, (int, float)) else raw_ram
    return {
        "$key": node.key,
        "name": node.name,
        "cpu_cores": node.get("cpu_cores"),
        "ram_gb": ram_gb,
        "status": node.get("status", ""),
        "is_enabled": node.get("enabled"),
        "cluster_name": node.get("cluster_name", ""),
        "host_node": node.get("host_node", ""),
    }


def _resolve_tenant_node(tenant_obj: Any, identifier: str) -> int:
    """Resolve a tenant node name or ID to a key."""
    if identifier.isdigit():
        return int(identifier)
    nodes = tenant_obj.nodes.list()
    matches = [n for n in nodes if n.name == identifier]
    if len(matches) == 1:
        return int(matches[0].key)
    if len(matches) > 1:
        typer.echo(
            f"Error: Multiple tenant nodes match '{identifier}'. Use a numeric key.",
            err=True,
        )
        raise typer.Exit(7)
    typer.echo(f"Error: Tenant node '{identifier}' not found.", err=True)
    raise typer.Exit(6)


@app.command("list")
@handle_errors()
def tenant_node_list(
    ctx: typer.Context,
    tenant: Annotated[str, typer.Argument(help="Tenant name or key")],
) -> None:
    """List compute nodes allocated to a tenant."""
    vctx, tenant_obj = _get_tenant(ctx, tenant)
    nodes = tenant_obj.nodes.list()
    data = [_tenant_node_to_dict(n) for n in nodes]
    output_result(
        data,
        output_format=vctx.output_format,
        query=vctx.query,
        columns=TENANT_NODE_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("get")
@handle_errors()
def tenant_node_get(
    ctx: typer.Context,
    tenant: Annotated[str, typer.Argument(help="Tenant name or key")],
    node: Annotated[str, typer.Argument(help="Node name or key")],
) -> None:
    """Get details of a tenant compute node."""
    vctx, tenant_obj = _get_tenant(ctx, tenant)
    node_key = _resolve_tenant_node(tenant_obj, node)
    node_obj = tenant_obj.nodes.get(node_key)
    output_result(
        _tenant_node_to_dict(node_obj),
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("create")
@handle_errors()
def tenant_node_create(
    ctx: typer.Context,
    tenant: Annotated[str, typer.Argument(help="Tenant name or key")],
    cpu_cores: Annotated[int, typer.Option("--cpu-cores", help="Number of CPU cores")],
    ram_gb: Annotated[int, typer.Option("--ram-gb", help="RAM in GB")],
    cluster: Annotated[int | None, typer.Option("--cluster", help="Cluster key")] = None,
    name: Annotated[str | None, typer.Option("--name", "-n", help="Node name")] = None,
    preferred_node: Annotated[
        int | None, typer.Option("--preferred-node", help="Preferred host node key")
    ] = None,
) -> None:
    """Allocate a compute node to a tenant."""
    vctx, tenant_obj = _get_tenant(ctx, tenant)

    create_kwargs: dict[str, Any] = {
        "cpu_cores": cpu_cores,
        "ram_gb": ram_gb,
    }
    if cluster is not None:
        create_kwargs["cluster"] = cluster
    if name is not None:
        create_kwargs["name"] = name
    if preferred_node is not None:
        create_kwargs["preferred_node"] = preferred_node

    node_obj = tenant_obj.nodes.create(**create_kwargs)

    output_success(
        f"Created tenant node '{node_obj.name}' (key: {node_obj.key})",
        quiet=vctx.quiet,
    )
    output_result(
        _tenant_node_to_dict(node_obj),
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("update")
@handle_errors()
def tenant_node_update(
    ctx: typer.Context,
    tenant: Annotated[str, typer.Argument(help="Tenant name or key")],
    node: Annotated[str, typer.Argument(help="Node name or key")],
    cpu_cores: Annotated[
        int | None, typer.Option("--cpu-cores", help="Number of CPU cores")
    ] = None,
    ram_gb: Annotated[int | None, typer.Option("--ram-gb", help="RAM in GB")] = None,
    name: Annotated[str | None, typer.Option("--name", "-n", help="New name")] = None,
    enabled: Annotated[
        bool | None, typer.Option("--enabled/--disabled", help="Enable/disable node")
    ] = None,
) -> None:
    """Update a tenant compute node."""
    vctx, tenant_obj = _get_tenant(ctx, tenant)
    node_key = _resolve_tenant_node(tenant_obj, node)

    updates: dict[str, Any] = {}
    if cpu_cores is not None:
        updates["cpu_cores"] = cpu_cores
    if ram_gb is not None:
        updates["ram"] = ram_gb * 1024  # SDK update accepts ram in MB
    if name is not None:
        updates["name"] = name
    if enabled is not None:
        updates["enabled"] = enabled

    if not updates:
        typer.echo("No updates specified.", err=True)
        raise typer.Exit(2)

    node_obj = tenant_obj.nodes.update(node_key, **updates)
    output_success(f"Updated tenant node '{node_obj.name}'", quiet=vctx.quiet)
    output_result(
        _tenant_node_to_dict(node_obj),
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("delete")
@handle_errors()
def tenant_node_delete(
    ctx: typer.Context,
    tenant: Annotated[str, typer.Argument(help="Tenant name or key")],
    node: Annotated[str, typer.Argument(help="Node name or key")],
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation")] = False,
) -> None:
    """Remove a compute node from a tenant."""
    vctx, tenant_obj = _get_tenant(ctx, tenant)
    node_key = _resolve_tenant_node(tenant_obj, node)

    if not confirm_action(f"Delete tenant node '{node}'?", yes=yes):
        typer.echo("Cancelled.")
        raise typer.Exit(0)

    tenant_obj.nodes.delete(node_key)
    output_success(f"Deleted tenant node '{node}'", quiet=vctx.quiet)
