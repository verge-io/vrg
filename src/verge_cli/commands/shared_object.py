"""Shared object management commands."""

from __future__ import annotations

from typing import Annotated, Any

import typer

from verge_cli.columns import SHARED_OBJECT_COLUMNS
from verge_cli.context import get_context
from verge_cli.errors import handle_errors
from verge_cli.multi import list_all_profiles
from verge_cli.output import output_result, output_success
from verge_cli.utils import confirm_action, resolve_resource_id

app = typer.Typer(
    name="shared-object",
    help="Manage shared objects between tenants.",
    no_args_is_help=True,
)


def _shared_object_to_dict(obj: Any) -> dict[str, Any]:
    """Convert a SharedObject SDK object to a dict for output."""
    return {
        "$key": obj.key,
        "name": getattr(obj, "name", obj.get("name", "")),
        "description": getattr(obj, "description", obj.get("description", "")),
        "tenant_key": getattr(obj, "tenant_key", obj.get("tenant_key")),
        "tenant_name": getattr(obj, "tenant_name", obj.get("tenant_name", "")),
        "object_type": getattr(obj, "object_type", obj.get("object_type", "")),
        "object_id": getattr(obj, "object_id", obj.get("object_id", "")),
        "is_inbox": getattr(obj, "is_inbox", obj.get("is_inbox", False)),
    }


@app.command("list")
@handle_errors()
def list_cmd(
    ctx: typer.Context,
    tenant: Annotated[
        int | None,
        typer.Option("--tenant", help="Filter by tenant key"),
    ] = None,
    inbox: Annotated[
        bool,
        typer.Option("--inbox", help="Show only inbox (received) objects"),
    ] = False,
) -> None:
    """List shared objects."""
    if ctx.obj.get("all_profiles"):
        list_all_profiles(
            ctx, lambda c: c.shared_objects.list(), _shared_object_to_dict, SHARED_OBJECT_COLUMNS
        )
        return
    vctx = get_context(ctx)
    kwargs: dict[str, Any] = {}
    if tenant is not None:
        kwargs["tenant_key"] = tenant
    if inbox:
        kwargs["inbox_only"] = True

    objects = vctx.client.shared_objects.list(**kwargs)
    data = [_shared_object_to_dict(o) for o in objects]
    output_result(
        data,
        output_format=vctx.output_format,
        query=vctx.query,
        columns=SHARED_OBJECT_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("get")
@handle_errors()
def get_cmd(
    ctx: typer.Context,
    shared_object: Annotated[str, typer.Argument(help="Shared object name or key")],
) -> None:
    """Get details of a shared object."""
    vctx = get_context(ctx)
    key = resolve_resource_id(vctx.client.shared_objects, shared_object, "Shared object")
    obj = vctx.client.shared_objects.get(key)
    output_result(
        _shared_object_to_dict(obj),
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("create")
@handle_errors()
def create_cmd(
    ctx: typer.Context,
    tenant_key: Annotated[int, typer.Option("--tenant-key", help="Tenant key to share with")],
    vm_name: Annotated[str | None, typer.Option("--vm-name", help="VM name to share")] = None,
    vm_key: Annotated[int | None, typer.Option("--vm-key", help="VM key to share")] = None,
    name: Annotated[str | None, typer.Option("--name", "-n", help="Shared object name")] = None,
    description: Annotated[
        str | None, typer.Option("--description", "-d", help="Description")
    ] = None,
    snapshot_name: Annotated[
        str | None, typer.Option("--snapshot-name", help="Snapshot name")
    ] = None,
) -> None:
    """Create a shared object (share a VM with a tenant)."""
    vctx = get_context(ctx)
    kwargs: dict[str, Any] = {"tenant_key": tenant_key}
    if vm_name is not None:
        kwargs["vm_name"] = vm_name
    if vm_key is not None:
        kwargs["vm_key"] = vm_key
    if name is not None:
        kwargs["name"] = name
    if description is not None:
        kwargs["description"] = description
    if snapshot_name is not None:
        kwargs["snapshot_name"] = snapshot_name

    result = vctx.client.shared_objects.create(**kwargs)
    output_success(
        f"Created shared object '{getattr(result, 'name', '')}' (key: {result.key})",
        quiet=vctx.quiet,
    )


@app.command("import")
@handle_errors()
def import_cmd(
    ctx: typer.Context,
    shared_object: Annotated[str, typer.Argument(help="Shared object name or key")],
) -> None:
    """Import (receive) a shared object."""
    vctx = get_context(ctx)
    key = resolve_resource_id(vctx.client.shared_objects, shared_object, "Shared object")
    vctx.client.shared_objects.import_object(key)
    output_success(f"Imported shared object '{shared_object}'", quiet=vctx.quiet)


@app.command("refresh")
@handle_errors()
def refresh_cmd(
    ctx: typer.Context,
    shared_object: Annotated[str, typer.Argument(help="Shared object name or key")],
) -> None:
    """Refresh a shared object."""
    vctx = get_context(ctx)
    key = resolve_resource_id(vctx.client.shared_objects, shared_object, "Shared object")
    vctx.client.shared_objects.refresh_object(key)
    output_success(f"Refreshed shared object '{shared_object}'", quiet=vctx.quiet)


@app.command("delete")
@handle_errors()
def delete_cmd(
    ctx: typer.Context,
    shared_object: Annotated[str, typer.Argument(help="Shared object name or key")],
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation")] = False,
) -> None:
    """Delete a shared object."""
    vctx = get_context(ctx)
    key = resolve_resource_id(vctx.client.shared_objects, shared_object, "Shared object")

    if not confirm_action(f"Delete shared object '{shared_object}'?", yes=yes):
        typer.echo("Cancelled.")
        raise typer.Exit(0)

    vctx.client.shared_objects.delete(key)
    output_success(f"Deleted shared object '{shared_object}'", quiet=vctx.quiet)
