"""Cloud snapshot management commands."""

from __future__ import annotations

from typing import Annotated, Any

import typer

from verge_cli.columns import (
    CLOUD_SNAPSHOT_COLUMNS,
    CLOUD_SNAPSHOT_TENANT_COLUMNS,
    CLOUD_SNAPSHOT_VM_COLUMNS,
)
from verge_cli.commands import snapshot_profile
from verge_cli.context import get_context
from verge_cli.errors import handle_errors
from verge_cli.multi import list_all_profiles
from verge_cli.output import output_result, output_success
from verge_cli.utils import confirm_action, resolve_resource_id

app = typer.Typer(
    name="snapshot",
    help=(
        "Manage VergeOS cloud snapshots (system-wide point-in-time captures).\n\n"
        "A **cloud snapshot** (also called a *system snapshot*) captures the"
        " entire VergeOS system state — every VM, tenant, and storage volume —"
        " at a single point in time. Cloud snapshots are the unit of data"
        " transported by site syncs and the basis for disaster recovery. They"
        " also support local recovery without any sync involvement. System"
        " limit: **2,048 snapshots** at any time.\n\n"
        "For structured output, pair any `list` or `get` with `-o json`. Useful"
        " fields to `--query`: `name`, `status`, `created`, `expires`,"
        " `immutable`, `private`. Name resolution applies to `get`, `delete`,"
        " `vms`, `tenants`, `restore-vm`, and `restore-tenant` — ambiguous"
        " names raise exit code 7 (multiple matches).\n\n"
        "---\n\n"
        "**Examples:**\n\n"
        "    # List current cloud snapshots\n"
        "    vrg snapshot list\n\n"
        "    # Include expired snapshots in the list\n"
        "    vrg snapshot list --include-expired\n\n"
        "    # Take a manual snapshot before a risky change\n"
        "    vrg snapshot create --name before-upgrade --immutable\n\n"
        "    # Get snapshot details as JSON\n"
        "    vrg -o json snapshot get before-upgrade\n\n"
        "    # Inspect which VMs a snapshot captured\n"
        "    vrg snapshot vms before-upgrade\n\n"
        "    # Restore a single VM from a snapshot with a new name\n"
        "    vrg snapshot restore-vm before-upgrade --vm web-01 --new-name web-01-restored\n\n"
        "    # Delete a snapshot (non-immutable) without confirmation\n"
        "    vrg snapshot delete 42 --yes\n\n"
        "---\n\n"
        "**Notes:**\n\n"
        "Cloud snapshots capture the entire system. For per-VM snapshots use"
        " `vrg vm snapshot`; for NAS volume snapshots use"
        " `vrg nas volume-snapshot`; for tenant-scoped snapshots use"
        " `vrg tenant snapshot`.\n\n"
        "Snapshot names must be unique system-wide. Without `--name`, VergeOS"
        " auto-generates one using the `Snapshot_%Y%m%d_%H%M` pattern.\n\n"
        "`--retention` (seconds) and `--never-expire` are mutually exclusive."
        " `--immutable` locks the snapshot against deletion until its immutable"
        " lock expires; deletion is blocked while locked.\n\n"
        "Automated snapshot scheduling lives under `vrg snapshot profile`"
        " (with periods defining cadence and retention)."
    ),
    no_args_is_help=True,
    rich_markup_mode="markdown",
)

app.add_typer(snapshot_profile.app, name="profile")


def _snapshot_to_dict(snap: Any) -> dict[str, Any]:
    """Convert a CloudSnapshot object to a dict for output."""
    return {
        "$key": snap.key,
        "name": snap.name,
        "status": snap.get("status"),
        "created": snap.get("created"),
        "expires": snap.get("expires"),
        "immutable": snap.get("immutable"),
        "private": snap.get("private"),
        "description": snap.get("description", ""),
    }


def _vm_to_dict(vm: Any) -> dict[str, Any]:
    """Convert a CloudSnapshotVM object to a dict for output."""
    return {
        "$key": vm.key,
        "name": vm.name,
        "status": vm.get("status"),
    }


def _tenant_to_dict(tenant: Any) -> dict[str, Any]:
    """Convert a CloudSnapshotTenant object to a dict for output."""
    return {
        "$key": tenant.key,
        "name": tenant.name,
        "status": tenant.get("status"),
    }


@app.command("list")
@handle_errors()
def list_cmd(
    ctx: typer.Context,
    include_expired: Annotated[
        bool,
        typer.Option("--include-expired", help="Include expired snapshots"),
    ] = False,
) -> None:
    """List all cloud snapshots."""
    if ctx.obj.get("all_profiles"):
        list_all_profiles(
            ctx, lambda c: c.cloud_snapshots.list(), _snapshot_to_dict, CLOUD_SNAPSHOT_COLUMNS
        )
        return
    vctx = get_context(ctx)
    snapshots = vctx.client.cloud_snapshots.list(include_expired=include_expired)
    data = [_snapshot_to_dict(s) for s in snapshots]
    output_result(
        data,
        output_format=vctx.output_format,
        query=vctx.query,
        columns=CLOUD_SNAPSHOT_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("get")
@handle_errors()
def get_cmd(
    ctx: typer.Context,
    snapshot: Annotated[str, typer.Argument(help="Snapshot name or key")],
) -> None:
    """Get details of a cloud snapshot."""
    vctx = get_context(ctx)
    key = resolve_resource_id(vctx.client.cloud_snapshots, snapshot, "Cloud snapshot")
    snap = vctx.client.cloud_snapshots.get(key)
    output_result(
        _snapshot_to_dict(snap),
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("create")
@handle_errors()
def create_cmd(
    ctx: typer.Context,
    name: Annotated[
        str | None,
        typer.Option("--name", "-n", help="Snapshot name (auto-generated if omitted)"),
    ] = None,
    retention: Annotated[
        int | None,
        typer.Option("--retention", help="Retention in seconds"),
    ] = None,
    never_expire: Annotated[
        bool,
        typer.Option("--never-expire", help="Snapshot never expires"),
    ] = False,
    immutable: Annotated[
        bool,
        typer.Option("--immutable", help="Make snapshot immutable"),
    ] = False,
    private: Annotated[
        bool,
        typer.Option("--private", help="Mark snapshot as private"),
    ] = False,
    wait: Annotated[
        bool,
        typer.Option("--wait", help="Wait for snapshot completion"),
    ] = False,
) -> None:
    """Create a new cloud snapshot."""
    # Mutual exclusion check
    if retention is not None and never_expire:
        typer.echo("Error: --retention and --never-expire are mutually exclusive.", err=True)
        raise typer.Exit(2)

    vctx = get_context(ctx)

    kwargs: dict[str, Any] = {
        "name": name,
        "immutable": immutable,
        "private": private,
        "wait": wait,
    }
    if never_expire:
        kwargs["never_expire"] = True
    elif retention is not None:
        kwargs["retention_seconds"] = retention

    result = vctx.client.cloud_snapshots.create(**kwargs)

    snap_name = result.name if result else (name or "snapshot")
    snap_key = result.key if result else "?"
    output_success(
        f"Created cloud snapshot '{snap_name}' (key: {snap_key})",
        quiet=vctx.quiet,
    )


@app.command("delete")
@handle_errors()
def delete_cmd(
    ctx: typer.Context,
    snapshot: Annotated[str, typer.Argument(help="Snapshot name or key")],
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation")] = False,
) -> None:
    """Delete a cloud snapshot."""
    vctx = get_context(ctx)
    key = resolve_resource_id(vctx.client.cloud_snapshots, snapshot, "Cloud snapshot")

    if not confirm_action(f"Delete cloud snapshot '{snapshot}'?", yes=yes):
        typer.echo("Cancelled.")
        raise typer.Exit(0)

    vctx.client.cloud_snapshots.delete(key)
    output_success(f"Deleted cloud snapshot '{snapshot}'", quiet=vctx.quiet)


@app.command("vms")
@handle_errors()
def vms_cmd(
    ctx: typer.Context,
    snapshot: Annotated[str, typer.Argument(help="Snapshot name or key")],
) -> None:
    """List VMs captured in a cloud snapshot."""
    vctx = get_context(ctx)
    key = resolve_resource_id(vctx.client.cloud_snapshots, snapshot, "Cloud snapshot")
    vms = vctx.client.cloud_snapshots.vms(key).list()
    data = [_vm_to_dict(v) for v in vms]
    output_result(
        data,
        output_format=vctx.output_format,
        query=vctx.query,
        columns=CLOUD_SNAPSHOT_VM_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("tenants")
@handle_errors()
def tenants_cmd(
    ctx: typer.Context,
    snapshot: Annotated[str, typer.Argument(help="Snapshot name or key")],
) -> None:
    """List tenants captured in a cloud snapshot."""
    vctx = get_context(ctx)
    key = resolve_resource_id(vctx.client.cloud_snapshots, snapshot, "Cloud snapshot")
    tenants = vctx.client.cloud_snapshots.tenants(key).list()
    data = [_tenant_to_dict(t) for t in tenants]
    output_result(
        data,
        output_format=vctx.output_format,
        query=vctx.query,
        columns=CLOUD_SNAPSHOT_TENANT_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("restore-vm")
@handle_errors()
def restore_vm_cmd(
    ctx: typer.Context,
    snapshot: Annotated[str, typer.Argument(help="Snapshot name or key")],
    vm: Annotated[str, typer.Option("--vm", help="VM name or key to restore")],
    new_name: Annotated[
        str | None,
        typer.Option("--new-name", help="Name for the restored VM"),
    ] = None,
) -> None:
    """Restore a VM from a cloud snapshot."""
    vctx = get_context(ctx)
    snap_key = resolve_resource_id(vctx.client.cloud_snapshots, snapshot, "Cloud snapshot")

    # Resolve VM within the snapshot
    kwargs: dict[str, Any] = {"snapshot_key": snap_key}
    if vm.isdigit():
        kwargs["vm_key"] = int(vm)
    else:
        kwargs["vm_name"] = vm
    if new_name:
        kwargs["new_name"] = new_name

    result = vctx.client.cloud_snapshots.restore_vm(**kwargs)
    output_success(f"Restored VM '{vm}' from snapshot '{snapshot}'", quiet=vctx.quiet)
    output_result(
        result,
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("restore-tenant")
@handle_errors()
def restore_tenant_cmd(
    ctx: typer.Context,
    snapshot: Annotated[str, typer.Argument(help="Snapshot name or key")],
    tenant: Annotated[str, typer.Option("--tenant", help="Tenant name or key to restore")],
    new_name: Annotated[
        str | None,
        typer.Option("--new-name", help="Name for the restored tenant"),
    ] = None,
) -> None:
    """Restore a tenant from a cloud snapshot."""
    vctx = get_context(ctx)
    snap_key = resolve_resource_id(vctx.client.cloud_snapshots, snapshot, "Cloud snapshot")

    kwargs: dict[str, Any] = {"snapshot_key": snap_key}
    if tenant.isdigit():
        kwargs["tenant_key"] = int(tenant)
    else:
        kwargs["tenant_name"] = tenant
    if new_name:
        kwargs["new_name"] = new_name

    result = vctx.client.cloud_snapshots.restore_tenant(**kwargs)
    output_success(f"Restored tenant '{tenant}' from snapshot '{snapshot}'", quiet=vctx.quiet)
    output_result(
        result,
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )
