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
    help="Manage tenant storage allocations.",
    no_args_is_help=True,
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
    """List storage allocations for a tenant."""
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
    """Get details of a tenant storage allocation."""
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
    """Allocate storage to a tenant."""
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
    """Update a tenant storage allocation."""
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
    """Remove a storage allocation from a tenant."""
    vctx, tenant_obj = _get_tenant(ctx, tenant)
    storage_key = _resolve_tenant_storage(tenant_obj, storage)

    if not confirm_action(f"Delete storage allocation '{storage}'?", yes=yes):
        typer.echo("Cancelled.")
        raise typer.Exit(0)

    tenant_obj.storage.delete(storage_key)
    output_success(f"Deleted storage allocation '{storage}'", quiet=vctx.quiet)
