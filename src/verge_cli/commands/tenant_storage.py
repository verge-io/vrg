"""Tenant storage allocation sub-resource commands."""

from __future__ import annotations

from typing import Annotated, Any

import typer

from verge_cli.columns import TENANT_STORAGE_COLUMNS
from verge_cli.context import get_context
from verge_cli.errors import handle_errors
from verge_cli.output import output_result, output_success
from verge_cli.utils import confirm_action, resolve_resource_id

app = typer.Typer(
    name="storage",
    help=(
        "Provision and adjust a tenant's per-tier storage quotas.\n\n"
        "**Tenant storage** is allocated one quota per [storage"
        " tier](https://verge.io): each row in this view represents the"
        " tenant's share of a single vSAN tier (typically tier 1 for NVMe,"
        " tier 2 for SAS SSD, tier 3 for SATA HDD — conventions, not"
        " enforced mappings). The tenant sees a storage system exactly as"
        " large as its `provisioned` quota and cannot allocate beyond it;"
        " enforcement happens at the vSAN layer. Quotas are sized and"
        " adjusted by the host operator — tenants cannot provision their"
        " own storage.\n\n"
        "Every command takes the tenant as the first argument (name or"
        " numeric key); the allocation itself is identified by numeric key."
        " Use `-o json` for machine-readable output; useful `--query`"
        " targets are `$key`, `tier_name`, `provisioned_gb`, `used_gb`,"
        " and `used_percent`. Tenant name lookups that match multiple"
        " tenants exit with code 7 — pass the numeric key to disambiguate."
        " Best practice: monitor `used_percent` and alert above 80% to"
        " avoid quota exhaustion before workloads start failing.\n\n"
        "---\n\n"
        "**Examples:**\n\n"
        "    # List a tenant's storage quotas across all tiers\n"
        "    vrg tenant storage list acme-corp\n\n"
        "    # JSON output for agents\n"
        "    vrg -o json tenant storage list acme-corp\n\n"
        "    # Include used GB and utilization percentage\n"
        "    vrg -o wide tenant storage list acme-corp\n\n"
        "    # Inspect one quota by its numeric key\n"
        "    vrg tenant storage get acme-corp 12\n\n"
        "    # Provision 500 GB on tier 2 (SAS SSD) for a tenant\n"
        "    vrg tenant storage create acme-corp --tier 2 --provisioned-gb 500\n\n"
        "    # Grow an existing quota to 1 TB total\n"
        "    vrg tenant storage update acme-corp 12 --provisioned-gb 1000\n\n"
        "    # Remove a quota without prompting\n"
        "    vrg tenant storage delete acme-corp 12 -y\n\n"
        "---\n\n"
        "**Notes:**\n\n"
        "`--provisioned-gb` on `update` is the new **total** quota, not a"
        " delta — pass the absolute target (e.g. `1000` to grow 500 GB to"
        " 1 TB). Shrinking a quota below current `used` bytes is rejected"
        " by the host; have the tenant delete VMs, volumes, or snapshots"
        " first. Deleting a quota frees the tier slot but fails if the"
        " tenant has data resident on that tier. Tiers 0-5 are cluster-wide"
        " conventions — the actual drive class backing a tier depends on"
        " node vSAN configuration, so confirm tier semantics against the"
        " cluster before sizing."
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


def _tenant_storage_to_dict(storage: Any) -> dict[str, Any]:
    """Convert a Tenant Storage object to a dict for output."""
    # SDK TenantStorage uses @property for computed values (tier_name,
    # provisioned_gb, used_gb, used_percent), so use attribute access.
    return {
        "$key": storage.key,
        "tier_name": storage.tier_name,
        "provisioned_gb": storage.provisioned_gb,
        "used_gb": storage.used_gb,
        "used_percent": storage.used_percent,
    }


def _resolve_tenant_storage(tenant_obj: Any, identifier: str) -> int:
    """Resolve a tenant storage name or ID to a key."""
    if identifier.isdigit():
        return int(identifier)
    items = tenant_obj.storage.list()
    matches = [s for s in items if s.name == identifier]
    if len(matches) == 1:
        return int(matches[0].key)
    if len(matches) > 1:
        typer.echo(
            f"Error: Multiple storage allocations match '{identifier}'. Use a numeric key.",
            err=True,
        )
        raise typer.Exit(7)
    typer.echo(f"Error: Storage allocation '{identifier}' not found.", err=True)
    raise typer.Exit(6)


@app.command("list")
@handle_errors()
def tenant_storage_list(
    ctx: typer.Context,
    tenant: Annotated[str, typer.Argument(help="Tenant name or key")],
) -> None:
    """List storage allocations for a tenant.

    One row per provisioned storage tier. Default columns show the key,
    tier name, and provisioned GB; use `-o wide` to include used GB and
    utilization percentage, or `-o json` for the full set.

    **Examples:**

        vrg tenant storage list acme-corp
        vrg -o wide tenant storage list acme-corp
        vrg -o json tenant storage list acme-corp --query '[].used_percent'
    """
    vctx, tenant_obj = _get_tenant(ctx, tenant)
    items = tenant_obj.storage.list()
    data = [_tenant_storage_to_dict(s) for s in items]
    output_result(
        data,
        output_format=vctx.output_format,
        query=vctx.query,
        columns=TENANT_STORAGE_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("get")
@handle_errors()
def tenant_storage_get(
    ctx: typer.Context,
    tenant: Annotated[str, typer.Argument(help="Tenant name or key")],
    storage: Annotated[str, typer.Argument(help="Storage name or key")],
) -> None:
    """Get details of a tenant storage allocation.

    The allocation is identified by its numeric key (shown in `list`).
    Pair with `-o json` for full field output.

    **Examples:**

        vrg tenant storage get acme-corp 12
        vrg -o json tenant storage get acme-corp 12
    """
    vctx, tenant_obj = _get_tenant(ctx, tenant)
    storage_key = _resolve_tenant_storage(tenant_obj, storage)
    storage_obj = tenant_obj.storage.get(storage_key)
    output_result(
        _tenant_storage_to_dict(storage_obj),
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("create")
@handle_errors()
def tenant_storage_create(
    ctx: typer.Context,
    tenant: Annotated[str, typer.Argument(help="Tenant name or key")],
    tier: Annotated[int, typer.Option("--tier", "-t", help="Storage tier number")],
    provisioned_gb: Annotated[int, typer.Option("--provisioned-gb", help="Provisioned size in GB")],
) -> None:
    """Allocate storage to a tenant on a given tier.

    Creates a new per-tier quota. `--tier` is the vSAN tier number (0-5;
    typically 1=NVMe, 2=SAS SSD, 3=SATA HDD). `--provisioned-gb` is the
    total quota in GB — the tenant will see a storage system exactly
    that large on the selected tier.

    **Examples:**

        # 500 GB on tier 2 (SAS SSD)
        vrg tenant storage create acme-corp --tier 2 --provisioned-gb 500

        # 2 TB archive tier
        vrg tenant storage create acme-corp -t 3 --provisioned-gb 2000
    """
    vctx, tenant_obj = _get_tenant(ctx, tenant)

    storage_obj = tenant_obj.storage.create(
        tier=tier,
        provisioned_gb=provisioned_gb,
    )

    output_success(
        f"Created storage allocation (key: {storage_obj.key})",
        quiet=vctx.quiet,
    )
    output_result(
        _tenant_storage_to_dict(storage_obj),
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("update")
@handle_errors()
def tenant_storage_update(
    ctx: typer.Context,
    tenant: Annotated[str, typer.Argument(help="Tenant name or key")],
    storage: Annotated[str, typer.Argument(help="Storage name or key")],
    provisioned_gb: Annotated[
        int | None, typer.Option("--provisioned-gb", help="New provisioned size in GB")
    ] = None,
) -> None:
    """Update a tenant storage allocation.

    `--provisioned-gb` is the new **total** quota, not a delta. Pass the
    absolute target (e.g. `1000` to grow a 500 GB quota to 1 TB). Shrinking
    below current `used` bytes is rejected by the host — have the tenant
    free space first.

    **Examples:**

        # Grow a quota to 1 TB total
        vrg tenant storage update acme-corp 12 --provisioned-gb 1000
    """
    vctx, tenant_obj = _get_tenant(ctx, tenant)
    storage_key = _resolve_tenant_storage(tenant_obj, storage)

    updates: dict[str, Any] = {}
    if provisioned_gb is not None:
        updates["provisioned"] = provisioned_gb * 1073741824

    if not updates:
        typer.echo("No updates specified.", err=True)
        raise typer.Exit(2)

    storage_obj = tenant_obj.storage.update(storage_key, **updates)
    output_success("Updated storage allocation", quiet=vctx.quiet)
    output_result(
        _tenant_storage_to_dict(storage_obj),
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("delete")
@handle_errors()
def tenant_storage_delete(
    ctx: typer.Context,
    tenant: Annotated[str, typer.Argument(help="Tenant name or key")],
    storage: Annotated[str, typer.Argument(help="Storage name or key")],
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation")] = False,
) -> None:
    """Remove a storage allocation from a tenant.

    Frees the tier slot. This is rejected if the tenant has data resident
    on that tier — have the tenant delete VMs, volumes, or snapshots first.
    Prompts for confirmation; pass `-y` to skip in scripts.

    **Examples:**

        vrg tenant storage delete acme-corp 12
        vrg tenant storage delete acme-corp 12 -y
    """
    vctx, tenant_obj = _get_tenant(ctx, tenant)
    storage_key = _resolve_tenant_storage(tenant_obj, storage)

    if not confirm_action(f"Delete storage allocation '{storage}'?", yes=yes):
        typer.echo("Cancelled.")
        raise typer.Exit(0)

    tenant_obj.storage.delete(storage_key)
    output_success(f"Deleted storage allocation '{storage}'", quiet=vctx.quiet)
