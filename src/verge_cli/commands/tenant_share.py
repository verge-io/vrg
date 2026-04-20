"""Tenant shared object sub-resource commands."""

from __future__ import annotations

from typing import Annotated, Any

import typer

from verge_cli.columns import ColumnDef, format_bool_yn, format_epoch
from verge_cli.context import get_context
from verge_cli.errors import handle_errors
from verge_cli.output import output_result, output_success
from verge_cli.utils import confirm_action, resolve_resource_id

app = typer.Typer(
    name="share",
    help=(
        "Share VM snapshots from the parent system into a tenant.\n\n"
        "**Shared objects** are the cross-tenant sharing mechanism VergeOS"
        " uses to push a VM snapshot from the parent system down to one of"
        " its tenants. The parent creates a shared object pointing at a"
        " specific VM snapshot; the tenant then runs `refresh` to re-fetch"
        " source metadata or `import` to materialize a local VM copy via"
        " the normal VM import pipeline. Only VM snapshots can be shared"
        " today (`type = vm`), and a tenant can hold up to 1,000 shared"
        " objects. Creation is one-way — tenants cannot create shared"
        " objects for themselves, only the parent can.\n\n"
        "Every shared object command takes a tenant as the first argument"
        " (name or numeric key). The share itself is identified by name"
        " within a tenant for `get`/`delete`, but `import` and `refresh`"
        " require the numeric key. Use `-o json` for machine-readable"
        " output; useful `--query` targets are `$key`, `name`,"
        " `tenant_name`, `object_type`, and `is_inbox`. Name lookups that"
        " match multiple objects exit with code 7 — pass the key to"
        " disambiguate.\n\n"
        "---\n\n"
        "**Examples:**\n\n"
        "    # List everything shared with a tenant\n"
        "    vrg tenant share list acme-corp\n\n"
        "    # List only items waiting in the tenant inbox\n"
        "    vrg tenant share list acme-corp --inbox\n\n"
        "    # Inspect a shared object by name\n"
        "    vrg -o json tenant share get acme-corp golden-web-image\n\n"
        "    # Push a VM's current snapshot into a tenant\n"
        "    vrg tenant share create acme-corp --vm web-01 --name"
        " golden-web-image\n\n"
        "    # Push a specific named snapshot instead of the latest\n"
        "    vrg tenant share create acme-corp --vm web-01 --snapshot"
        " release-2025-10 --name golden-web-image\n\n"
        "    # Tenant re-checks source metadata for updates\n"
        "    vrg tenant share refresh acme-corp 42\n\n"
        "    # Tenant imports the shared snapshot as a local VM\n"
        "    vrg tenant share import acme-corp 42\n\n"
        "    # Revoke a shared object\n"
        "    vrg tenant share delete acme-corp golden-web-image -y\n\n"
        "---\n\n"
        "**Notes:**\n\n"
        "`import` kicks off the full VM import pipeline inside the tenant"
        " and returns once the job is initiated — track progress with"
        " `vrg task list` in the tenant context. When an inbox-gated share"
        " is created, the tenant must explicitly accept it before the"
        " object appears in their working environment; `--inbox` on `list`"
        " surfaces those pending items. Deleting a shared object cascades"
        " to any in-flight import jobs that originated from it."
    ),
    no_args_is_help=True,
    rich_markup_mode="markdown",
)

SHARE_COLUMNS: list[ColumnDef] = [
    ColumnDef("$key", header="Key"),
    ColumnDef("name"),
    ColumnDef("tenant_name", header="Tenant"),
    ColumnDef("object_type", header="Type"),
    ColumnDef(
        "is_inbox",
        header="Inbox",
        format_fn=format_bool_yn,
        style_map={"Y": "yellow", "-": "dim"},
    ),
    ColumnDef("description", wide_only=True),
    ColumnDef("created_at", header="Created", format_fn=format_epoch, wide_only=True),
]


def _share_to_dict(obj: Any) -> dict[str, Any]:
    """Convert a SharedObject to a dict for output."""
    created_at = obj.created_at
    return {
        "$key": int(obj.key),
        "name": obj.name,
        "description": obj.description or "",
        "tenant_name": obj.tenant_name or "",
        "object_type": obj.object_type or "",
        "is_inbox": obj.is_inbox,
        "created_at": created_at.timestamp() if created_at else None,
    }


def _resolve_share(client: Any, tenant_key: int, identifier: str) -> int:
    """Resolve a shared object name or numeric key to a key."""
    if identifier.isdigit():
        return int(identifier)
    # Look up by name within the tenant
    obj = client.shared_objects.get(tenant_key=tenant_key, name=identifier)
    return int(obj.key)


@app.command("list")
@handle_errors()
def share_list(
    ctx: typer.Context,
    tenant: Annotated[str, typer.Argument(help="Tenant name or key")],
    inbox: Annotated[
        bool, typer.Option("--inbox", help="Show only inbox items (pending import)")
    ] = False,
) -> None:
    """List shared objects for a tenant."""
    vctx = get_context(ctx)
    tenant_key = resolve_resource_id(vctx.client.tenants, tenant, "Tenant")
    items = vctx.client.shared_objects.list(tenant_key=tenant_key, inbox_only=inbox)
    data = [_share_to_dict(i) for i in items]
    output_result(
        data,
        output_format=vctx.output_format,
        query=vctx.query,
        columns=SHARE_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("get")
@handle_errors()
def share_get(
    ctx: typer.Context,
    tenant: Annotated[str, typer.Argument(help="Tenant name or key")],
    share: Annotated[str, typer.Argument(help="Shared object name or key")],
) -> None:
    """Get details of a shared object."""
    vctx = get_context(ctx)
    tenant_key = resolve_resource_id(vctx.client.tenants, tenant, "Tenant")

    if share.isdigit():
        obj = vctx.client.shared_objects.get(int(share))
    else:
        obj = vctx.client.shared_objects.get(tenant_key=tenant_key, name=share)

    output_result(
        _share_to_dict(obj),
        columns=SHARE_COLUMNS,
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("create")
@handle_errors()
def share_create(
    ctx: typer.Context,
    tenant: Annotated[str, typer.Argument(help="Tenant name or key")],
    vm: Annotated[str, typer.Option("--vm", help="VM name or key to share")],
    name: Annotated[
        str | None, typer.Option("--name", "-n", help="Name for the shared object")
    ] = None,
    description: Annotated[
        str | None,
        typer.Option("--description", "-d", help="Description"),
    ] = None,
    snapshot: Annotated[
        str | None,
        typer.Option("--snapshot", help="Share a specific snapshot of the VM"),
    ] = None,
) -> None:
    """Share a VM with a tenant."""
    vctx = get_context(ctx)
    tenant_key = resolve_resource_id(vctx.client.tenants, tenant, "Tenant")
    vm_key = resolve_resource_id(vctx.client.vms, vm, "VM")

    kwargs: dict[str, Any] = {
        "tenant_key": tenant_key,
        "vm_key": vm_key,
    }
    if name is not None:
        kwargs["name"] = name
    if description is not None:
        kwargs["description"] = description
    if snapshot is not None:
        kwargs["snapshot_name"] = snapshot

    obj = vctx.client.shared_objects.create(**kwargs)

    output_success(
        f"Shared VM (key: {vm_key}) with tenant (key: {tenant_key}) as '{obj.name}' (key: {obj.key})",
        quiet=vctx.quiet,
    )
    output_result(
        _share_to_dict(obj),
        columns=SHARE_COLUMNS,
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("import")
@handle_errors()
def share_import(
    ctx: typer.Context,
    tenant: Annotated[str, typer.Argument(help="Tenant name or key")],
    share: Annotated[str, typer.Argument(help="Shared object key")],
) -> None:
    """Import a shared object into the tenant (creates a VM copy)."""
    vctx = get_context(ctx)
    resolve_resource_id(vctx.client.tenants, tenant, "Tenant")
    share_key = int(share)

    result = vctx.client.shared_objects.import_object(key=share_key)
    output_success(
        f"Import initiated for shared object (key: {share_key})",
        quiet=vctx.quiet,
    )
    if result:
        output_result(
            result,
            output_format=vctx.output_format,
            query=vctx.query,
            quiet=vctx.quiet,
            no_color=vctx.no_color,
        )


@app.command("refresh")
@handle_errors()
def share_refresh(
    ctx: typer.Context,
    tenant: Annotated[str, typer.Argument(help="Tenant name or key")],
    share: Annotated[str, typer.Argument(help="Shared object key")],
) -> None:
    """Refresh a shared object's data from the source."""
    vctx = get_context(ctx)
    resolve_resource_id(vctx.client.tenants, tenant, "Tenant")
    share_key = int(share)

    vctx.client.shared_objects.refresh_object(key=share_key)
    output_success(
        f"Refresh initiated for shared object (key: {share_key})",
        quiet=vctx.quiet,
    )


@app.command("delete")
@handle_errors()
def share_delete(
    ctx: typer.Context,
    tenant: Annotated[str, typer.Argument(help="Tenant name or key")],
    share: Annotated[str, typer.Argument(help="Shared object name or key")],
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation")] = False,
) -> None:
    """Delete a shared object."""
    vctx = get_context(ctx)
    tenant_key = resolve_resource_id(vctx.client.tenants, tenant, "Tenant")
    share_key = _resolve_share(vctx.client, tenant_key, share)

    if not confirm_action(f"Delete shared object (key: {share_key})?", yes=yes):
        raise typer.Abort()

    vctx.client.shared_objects.delete(key=share_key)
    output_success(
        f"Deleted shared object (key: {share_key})",
        quiet=vctx.quiet,
    )
